from pathlib import Path

import shutil
import json
import pytest

from yabu_cmd.controller import Backup, ProgressInfo
from yabu_cmd.model import PresetManager
from yabu_cmd.model import BackupManager


class TestBackupManager:
    @pytest.fixture
    def setup_create_backups_force_no_keep(self):
        import json

        temp_dir = Path("temp")
        folder = temp_dir.joinpath("folder")
        file = folder.joinpath("file.txt")
        folder.mkdir(parents=True)
        file.touch()  # set up rudamentary test environment
        file.write_text("This is a test file. :)")  # :)
        preset_json_file = Path(temp_dir.joinpath("presets.json"))
        preset_json_file.touch()
        presets_data = {
            "format": 1,
            "presets": {
                "testFolder": {
                    "targets": [str(folder.absolute())],
                    "destinations": [
                        {
                            "path": str(temp_dir),
                            "file_format": "zip",
                            "date_format": "%Y_%m_%d__%H%M%S%f",
                            "max_backup_count": 3,
                            "name_separator": "-",
                        }
                    ],
                },
                "testFile": {
                    "targets": [str(file.absolute())],
                    "destinations": [
                        {
                            "path": str(temp_dir),
                            "file_format": "zip",
                            "date_format": "%d_%m_%y__%H%M%S%f",
                            "max_backup_count": 3,
                            "name_separator": "-",
                        }
                    ],
                },
            },
        }
        preset_json_file.write_text(json.dumps(presets_data, indent=4))
        yield preset_json_file
        shutil.rmtree(temp_dir)

    def test_create_backups_zip_no_force_no_keep(self, preset_json):
        preset_manager = PresetManager(preset_json)
        presets = preset_manager.get_presets()
        backup_manager = BackupManager()
        for preset in presets:
            print(preset)
            for backup in backup_manager.create_backups(preset, False, False):
                if isinstance(backup, ProgressInfo):
                    continue
                assert isinstance(backup, Backup)
                if preset.name == "testFile":
                    assert backup.name == "file"
                    assert backup.date_format == "%Y_%m_%d__%H%M%S"
                    assert backup.name_separator == "-"
                    assert str(backup.target) == str(
                        Path("temp/folder/sub_folder/file.txt").absolute()
                    )  # allows Path and its children to equate. :)
                if preset.name == "testFolder":
                    assert backup.name == "folder"
                    assert backup.date_format == "%Y_%m_%d__%H%M%S"
                    assert backup.name_separator == "-"
                    assert str(backup.target) == str(
                        Path("temp/folder").absolute()
                    )  # allows Path and its children to equate. :)

    def test_create_backups_zip_force_no_keep(self, preset_json):
        preset_manager = PresetManager(preset_json)
        presets = preset_manager.get_presets()
        backup_manager = BackupManager()
        for i in range(4):
            for preset in presets:
                for destination in preset._destinations:
                    destination.date_format = "%Y_%m_%d__%H%M%S%f"  # these need to include the microseconds due to the rate at which backups are created.
                for backup in backup_manager.create_backups(preset, True, False):
                    if isinstance(backup, ProgressInfo):
                        continue
                    assert isinstance(backup, Backup)
        testFile_count = 0
        testFolder_count = 0
        for file in Path("temp").glob("file*.zip"):
            testFile_count += 1
        for file in Path("temp").glob("folder*.zip"):
            testFolder_count += 1
        assert testFile_count == 3
        assert testFolder_count == 3

    def test_create_backups_zip_force_keep(self, preset_json):
        preset_manager = PresetManager(preset_json)
        presets = preset_manager.get_presets()
        backup_manager = BackupManager()
        for i in range(4):
            print(i)
            for preset in presets:
                for destination in preset._destinations:
                    destination.date_format = "%Y_%m_%d__%H%M%S%f"  # these need to include the microseconds due to the rate at which backups are created.
                for backup in backup_manager.create_backups(preset, True, True):
                    if isinstance(backup, ProgressInfo):
                        continue
                    assert isinstance(backup, Backup)
        testFile_count = 0
        testFolder_count = 0
        for file in Path("temp").glob("file*.zip"):
            testFile_count += 1
        for file in Path("temp").glob("folder*.zip"):
            testFolder_count += 1
        assert testFile_count == 4
        assert testFolder_count == 4

    def test_metafile_generation(self, preset_json):
        preset_manager = PresetManager(preset_json)
        preset = preset_manager["testFolder"]
        target = preset._targets[0]
        destination = preset._destinations[0]
        backup_manager = BackupManager()
        md5_hash = None
        for i in backup_manager.create_md5_hash(target):
            if isinstance(i, ProgressInfo):
                continue
            if isinstance(i, str):
                md5_hash = i
        metafile_str = backup_manager._create_metafile(target, destination, md5_hash)

        metafile_json = json.loads(metafile_str)

        assert len(metafile_json.keys()) == 5
        assert metafile_json['target'] == str(target)
        assert metafile_json['name_separator'] == destination.name_separator
        assert metafile_json['date_format'] == destination.date_format
        assert metafile_json['content_hash'] == md5_hash
        assert metafile_json['content_type'] == "folder"
