"""Jupyter Server 2.21.0 / Tornado 6.5.9의 정적 파일 초기화 차이를 보완한다.

검토 서버 전용. Tornado의 실제 경로·심볼릭 링크 경계 검사는 그대로 호출한다.
"""
import os
from importlib.metadata import version
from jupyter_server.base.handlers import FileFindHandler

if version('jupyter_server') != '2.21.0' or version('tornado') != '6.5.9':
    raise RuntimeError('검토한 버전과 다릅니다. 호환 설정을 재검토하세요.')

original_validate = FileFindHandler.validate_absolute_path

def validate_with_selected_root(self, root, absolute_path):
    if absolute_path:
        selected = next((p for p in self.root if (absolute_path + os.sep).startswith(p)), self.root[0])
        self.allowed_symlink_directory = selected
    return original_validate(self, root, absolute_path)

FileFindHandler.validate_absolute_path = validate_with_selected_root
