"""Reusable image-to-video application service; offline indexing stays separate."""
import copy
import hashlib
import io
import json
import threading
import time
import warnings
from pathlib import Path
from uuid import uuid4
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError
from .core import ContractError, PROJECT, digest, file_hash, assert_snapshot, inventory
from .file_snapshot import FrozenFiles, input_files, stat_inventory
from .retrieval import ExactFrameIndex
from .storage_mysql import revisions
from .storage_mysql.connection import connect
from .storage_mysql.repository import rows
from .storage_mysql.service import load_index, select_generation


def read_query(path):
    path = Path(path)
    try:
        if not path.is_file() or path.stat().st_size > 64*1024*1024:
            raise ContractError('Query must be an existing image file of at most 64 MiB')
        raw = path.read_bytes()
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as source:
                image_format = source.format
                source.load()
                original = ImageOps.exif_transpose(source).convert('RGB')
        if min(original.size) < 3:
            raise ContractError('Query image is too small')
        return raw, original, image_format
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError('Cannot decode query image; choose a valid supported image') from None


class SearchSession:
    """Load and validate once, serialize GPU requests, invalidate changed inputs.

    Windows holds read-only sharing handles for the verified source/model files.
    Other platforms rehash source/model bytes before each query. MySQL DML
    revisions, row counts, trigger definitions and active pointer are checked
    before and after every query; changed snapshots require a new session.
    """
    def __init__(self, spec, cfg, index=None):
        self.spec = copy.deepcopy(spec); self.cfg = copy.deepcopy(cfg); self.index_arg = index
        if cfg.get('database', {}).get('backend') != 'mysql':
            raise ContractError('SearchSession requires the configured MySQL backend')
        self.started = False; self.closed = False; self.lease = None; self.encoder = None
        self.lock = threading.RLock(); self.queries = 0; self.initialization = {}

    def __enter__(self): return self
    def __exit__(self, *args): self.close()

    def close(self):
        if self.lease is not None:
            self.lease.close(); self.lease = None
        self.encoder = None
        self.closed = True

    def _start(self):
        from .features import FrameExtractor
        from .building import implementation_hash
        from .pipeline import runtime_identity
        start = time.perf_counter()
        try:
            self.generation = select_generation(self.cfg, self.index_arg)
            revisions.ensure_tracking(self.cfg)
            self.database_stamp = revisions.stamp(self.cfg, self.generation)
            self.lease = FrozenFiles(input_files(self.spec, self.cfg))
            self.files = stat_inventory(self.spec, self.cfg)
            index_start = time.perf_counter()
            self.frames, self.paths, self.model, self.label, self.context, self.index_report = load_index(
                self.spec, self.cfg, self.generation, metadata=True)
            self.feature_index = ExactFrameIndex(self.frames)
            self.by_frame = {(f['video_id'], f['index']): f for f in self.frames}
            with connect(self.cfg) as con:
                self.artifacts = {vid: json.loads(value) for vid, value in rows(con, 'video_artifacts', self.generation)}
            self.initialization['index_validation_and_load'] = time.perf_counter()-index_start
            self.code = implementation_hash()
            self.contract_file = file_hash(PROJECT/'report_spec.json')
            self.packages = runtime_identity()
            self._guard()
            model_start = time.perf_counter()
            self.encoder = FrameExtractor(self.spec, model_path=self.cfg['model_path'], revision=self.cfg['model_revision'],
                                          device=self.cfg['device'], local_files_only=self.cfg['local_files_only'])
            self.initialization['model_load'] = time.perf_counter()-model_start
            self._guard()
            self.started = True
            self.initialization['total'] = time.perf_counter()-start
        except BaseException:
            self.close(); raise

    def _guard(self):
        from .building import implementation_hash
        from .pipeline import model_identity, runtime_identity
        try:
            if self.closed:
                raise ContractError('Search session is closed; open a new session')
            if stat_inventory(self.spec, self.cfg) != self.files:
                raise ContractError('Source/model files changed during search session')
            if not self.lease.enforced:
                assert_snapshot(json.loads(self.context['build']['snapshot_json']), inventory(self.cfg['dataset_root'], self.spec))
                if model_identity(self.cfg) != self.model:
                    raise ContractError('Model bytes changed during search session')
            if implementation_hash() != self.code or file_hash(PROJECT/'report_spec.json') != self.contract_file or runtime_identity() != self.packages:
                raise ContractError('Runtime implementation/spec/dependencies changed during search session')
            if select_generation(self.cfg, self.index_arg) != self.generation or revisions.stamp(self.cfg, self.generation) != self.database_stamp:
                raise ContractError('MySQL index changed during search session; reopen it')
        except BaseException:
            self.close(); raise

    def query(self, image_path):
        with self.lock:
            if self.closed:
                raise ContractError('Search session is closed; open a new session')
            total_start = time.perf_counter(); times = {}
            start = time.perf_counter()
            raw, original, image_format = read_query(image_path)
            times['read_image'] = time.perf_counter()-start
            cold = not self.started
            if cold: self._start()
            start = time.perf_counter(); self._guard(); times['guard_before'] = time.perf_counter()-start
            from .preprocess import resize_short, content_box, prepare_image, square_for_clip
            start = time.perf_counter()
            decoded = resize_short(original, self.spec['sampling']['decode_short_side'])
            box = content_box([decoded], self.spec)
            prepared = prepare_image(original, self.spec, box=box)
            preprocess = dict(input_format=image_format, original_size=original.size, decoded_size=decoded.size,
                              crop_box=box, crop_coordinates='pixels_on_decode_short_360', prepared_size=prepared.size,
                              clip_square_size=square_for_clip(prepared).size, clip_input_size=[224,224])
            times['preprocess'] = time.perf_counter()-start
            start = time.perf_counter(); vectors = self.encoder.extract([prepared])[0]; times['encode'] = time.perf_counter()-start
            start = time.perf_counter(); hits = self.feature_index.rank(vectors, self.cfg['search']['weights']); times['search'] = time.perf_counter()-start
            for hit in hits:
                hit['video_path'] = str(Path(self.cfg['dataset_root'])/self.paths[hit['video_id']])
                path = Path(hit['image_path'])
                expected = self.artifacts[hit['video_id']].get(str(path))
                if not Path(hit['video_path']).is_file() or not path.is_file() or not expected or file_hash(path) != expected:
                    raise ContractError('Result video/keyframe is missing or changed')
            start = time.perf_counter(); self._guard(); times['guard_after'] = time.perf_counter()-start
            folder = Path(self.cfg['artifacts'])/('query-'+uuid4().hex); folder.mkdir(parents=True)
            start = time.perf_counter()
            from .result_export import export_videos
            from .quality_registry import summary as review_summary
            source_snapshot=json.loads(self.context['build']['snapshot_json'])
            export_videos(folder,hits,{r['video_id']:r['sha256'] for r in source_snapshot})
            times['export'] = time.perf_counter()-start
            start=time.perf_counter()
            quality=review_summary(self.cfg,source_snapshot,self.index_report['dataset_quality_status'])
            (folder/'quality-review.json').write_text(json.dumps(quality,ensure_ascii=False,indent=2),encoding='utf-8')
            (folder/'source-image.bin').write_bytes(raw)
            original.save(folder/'input.png'); prepared.save(folder/'preprocessed.png')
            square_for_clip(prepared).resize((224,224), Image.Resampling.BICUBIC).save(folder/'clip-input-preview.png')
            from .query_evidence import histogram_svg, verify_trace
            (folder/'histograms.svg').write_text(histogram_svg(vectors), encoding='utf-8')
            np.savez_compressed(folder/'query-features.npz', **vectors)
            matched = {f'{h["video_id"]}/{h["frame_index"]}': {name: v.tolist() for name, v in self.by_frame[(h['video_id'],h['frame_index'])]['features'].items()} for h in hits}
            trace = dict(trace_version='nd4-v2', query_sha256=hashlib.sha256(raw).hexdigest(), spec_hash=digest(self.spec),
                         model_identity=self.model, implementation_hash=self.code, index=self.label, index_revision=self.database_stamp[0][0],
                         search_policy=self.cfg['search'], query_features={k:v.tolist() for k,v in vectors.items()},
                         matched_features=matched, preprocess=preprocess, hits=hits,
                         dataset_quality_status=quality['status'],quality_review=quality,
                         retrieval=self.feature_index.last_statistics,
                         session=dict(cold=cold, query_number=self.queries+1, source_guard='windows_read_only_share_lease' if self.lease.enforced else 'full_sha256_each_query',
                                      initialization_seconds=self.initialization),
                         artifact_sha256={p.relative_to(folder).as_posix():file_hash(p) for p in folder.rglob('*') if p.is_file()})
            times['evidence'] = time.perf_counter()-start
            times['total'] = time.perf_counter()-total_start
            trace['timings_seconds'] = times
            (folder/'trace.json').write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding='utf-8')
            start = time.perf_counter()
            verify_trace(folder/'trace.json')
            times['score_replay'] = time.perf_counter()-start
            from .demo import render
            start = time.perf_counter()
            render(folder, trace)
            times['render'] = time.perf_counter()-start
            times['total'] = time.perf_counter()-total_start
            (folder/'trace.json').write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding='utf-8')
            self.queries += 1
            return str(folder/'demo.html')
