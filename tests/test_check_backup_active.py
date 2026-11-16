import time
from unittest.mock import MagicMock

import requests

from proxlb.utils.helper import Helper


def _proxlb_data(enable: bool = True) -> MagicMock:
    data = MagicMock()
    data.meta.balancing.backup_guard.enable = enable
    data.meta.balancing.backup_guard.lead_minutes = 30
    data.nodes = {"node1": MagicMock(), "node2": MagicMock()}
    return data


def _proxmox_api(tasks: list[dict[str, object]], backup_jobs: list[dict[str, object]]) -> MagicMock:
    api = MagicMock()
    api.nodes.return_value.tasks.get.return_value = tasks
    api.cluster.backup.get.return_value = backup_jobs
    return api


def test_check_backup_active_returns_false_when_disabled() -> None:
    proxmox_api = _proxmox_api([{"type": "vzdump"}], [])

    assert Helper.check_backup_active(proxmox_api, _proxlb_data(enable=False)) is False
    proxmox_api.nodes.assert_not_called()


def test_check_backup_active_returns_true_when_vzdump_task_is_running() -> None:
    proxmox_api = _proxmox_api([{"type": "vzdump"}], [])

    assert Helper.check_backup_active(proxmox_api, _proxlb_data()) is True


def test_check_backup_active_returns_true_when_job_starts_within_lead_time() -> None:
    proxmox_api = _proxmox_api([], [{"id": "backup-1", "enabled": 1, "next-run": time.time() + 600}])

    assert Helper.check_backup_active(proxmox_api, _proxlb_data()) is True


def test_check_backup_active_ignores_disabled_and_later_jobs() -> None:
    proxmox_api = _proxmox_api([], [
        {"id": "backup-1", "enabled": 0, "next-run": time.time() + 600},
        {"id": "backup-2", "enabled": 1, "next-run": time.time() + 7200},
    ])

    assert Helper.check_backup_active(proxmox_api, _proxlb_data()) is False


def test_check_backup_active_returns_true_on_connection_error() -> None:
    proxmox_api = _proxmox_api([], [])
    proxmox_api.cluster.backup.get.side_effect = requests.exceptions.ConnectionError("unreachable")

    assert Helper.check_backup_active(proxmox_api, _proxlb_data()) is True
