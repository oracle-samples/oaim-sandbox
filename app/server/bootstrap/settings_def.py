"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""

from common.schema import SettingsModel


def main() -> list[dict]:
    """Define example Settings Support"""
    clients = ["default", "server"]
    settings_objects = [SettingsModel(client=client) for client in clients]
    return settings_objects


if __name__ == "__main__":
    main()
