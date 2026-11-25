"""A verified Windows read session holds sharing leases instead of rehashing large media."""
import os
from pathlib import Path
from .core import ContractError


def input_files(spec, cfg):
    paths = []
    for folder in spec['classes']:
        directory = Path(cfg['dataset_root']) / folder
        if not directory.is_dir():
            raise ContractError('Missing source class directory')
        paths.extend(p.resolve() for p in directory.iterdir() if p.is_file() and p.suffix.lower() == '.mp4')
    if cfg.get('model_path'):
        model = Path(cfg['model_path'])
        paths.extend(p.resolve() for p in model.rglob('*') if p.is_file())
    return sorted(paths)


def stat_inventory(spec, cfg):
    return {str(p): (p.stat().st_size, p.stat().st_mtime_ns, p.stat().st_ctime_ns, p.stat().st_ino)
            for p in input_files(spec, cfg)}


class FrozenFiles:
    def __init__(self, paths):
        self.handles = []
        self.enforced = os.name == 'nt'
        if not self.enforced:
            return
        import ctypes
        from ctypes import wintypes
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                                            wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        self.kernel.CreateFileW.restype = wintypes.HANDLE
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel.CloseHandle.restype = wintypes.BOOL
        try:
            for path in paths:
                # GENERIC_READ, FILE_SHARE_READ, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL.
                handle = self.kernel.CreateFileW(str(path), 0x80000000, 1, None, 3, 0x80, None)
                if handle == ctypes.c_void_p(-1).value:
                    raise ContractError(f'Cannot hold a read-only source/model snapshot: {Path(path).name}; close any writer and retry')
                self.handles.append(handle)
        except BaseException:
            self.close(); raise

    def close(self):
        for handle in self.handles:
            self.kernel.CloseHandle(handle)
        self.handles.clear()
