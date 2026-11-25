PRAGMA foreign_keys=ON;
CREATE TABLE build (
 id INTEGER PRIMARY KEY CHECK(id=1), status TEXT NOT NULL CHECK(status IN ('building','ready','failed')),
 spec_hash TEXT NOT NULL, implementation_version TEXT NOT NULL,
 model_identity TEXT NOT NULL, snapshot_json TEXT NOT NULL, created_at TEXT NOT NULL,
 implementation_hash TEXT NOT NULL DEFAULT '', dataset_root TEXT NOT NULL DEFAULT '',
 quality_status TEXT NOT NULL DEFAULT 'pending', completed_at TEXT
);
CREATE TABLE videos (
 video_id TEXT PRIMARY KEY, class_code TEXT NOT NULL, relative_path TEXT NOT NULL UNIQUE,
 sha256 TEXT NOT NULL, size_bytes INTEGER NOT NULL, metadata_json TEXT NOT NULL,
 crop_json TEXT NOT NULL, quality_json TEXT NOT NULL
);
CREATE TABLE keyframes (
 video_id TEXT NOT NULL REFERENCES videos(video_id), frame_index INTEGER NOT NULL,
 target_time REAL NOT NULL, actual_time REAL NOT NULL, image_path TEXT NOT NULL,
 PRIMARY KEY(video_id,frame_index)
);
CREATE TABLE frame_features (
 video_id TEXT NOT NULL, frame_index INTEGER NOT NULL,
 feature TEXT NOT NULL CHECK(feature IN ('hsv','lbp','clip')), vector BLOB NOT NULL,
 PRIMARY KEY(video_id,frame_index,feature),
 FOREIGN KEY(video_id,frame_index) REFERENCES keyframes(video_id,frame_index),
 CHECK((feature='hsv' AND length(vector)=512) OR (feature='lbp' AND length(vector)=40)
 OR (feature='clip' AND length(vector)=2048))
);
CREATE TABLE video_features (
 video_id TEXT PRIMARY KEY REFERENCES videos(video_id),
 feature TEXT NOT NULL CHECK(feature='motion'), vector BLOB NOT NULL CHECK(length(vector)=96)
);
CREATE TABLE feature_catalog (
 feature TEXT PRIMARY KEY, dimension INTEGER NOT NULL, normalization TEXT NOT NULL, distance TEXT NOT NULL
);
CREATE INDEX keyframes_by_video ON keyframes(video_id);
CREATE TABLE video_artifacts (
 video_id TEXT PRIMARY KEY REFERENCES videos(video_id), manifest_json TEXT NOT NULL
);
