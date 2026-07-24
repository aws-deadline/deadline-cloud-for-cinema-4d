#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Setup runner for Cinema 4D integration tests."""

import argparse
import hashlib
import os
import platform
import subprocess
import sys
from pathlib import Path

import boto3
from botocore.config import Config

C4D_INSTALLERS = {
    "2025": {
        "windows": {
            "s3_key": "cinema4d/2025/Cinema4D_2025_2025.3.3_Win.zip",
            "sha256": "fcf0ea40af73727f1bc1fb1a47ea0c2f3476f0652824d3b740181dc1a6123e09",
            "type": "zip",
        },
        "macos": {
            "s3_key": "cinema4d/2025/Cinema4D_2025_2025.3.3_Mac.dmg",
            "sha256": "ff06ebae0ba37720049dfff044b75a5e9090dd94ba4f6f286f8889629e783ad8",
            "type": "dmg",
        },
    },
    "2026": {
        "windows": {
            "s3_key": "cinema4d/2026/Cinema4D_2026_2026.3.3_Win.exe",
            "sha256": "4dcfb6ea44fd45dcf6c77a4540f47fcaea1c322440d564cbd40c0a03ad7de681",
            "type": "exe",
        },
        "macos": {
            "s3_key": "cinema4d/2026/Cinema4D_2026_2026.3.3_Mac.dmg",
            "sha256": "ad758efdb24e0ee01e126a4e8ee54f148981a583bb84f8f832eedcbf1793716f",
            "type": "dmg",
        },
    },
}

C4D_INSTALL_PATHS = {
    "2025": {
        "windows": Path("C:/Program Files/Maxon Cinema 4D 2025"),
        "macos": Path("/Applications/Maxon Cinema 4D 2025"),
    },
    "2026": {
        "windows": Path("C:/Program Files/Maxon Cinema 4D 2026"),
        "macos": Path("/Applications/Maxon Cinema 4D 2026"),
    },
}


def run(cmd, check=True):
    """Run a shell command, exiting on failure if check is True."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if check and result.returncode != 0:
        sys.exit(result.returncode)
    return result


def download_from_s3(s3_path, local_path):
    """Download a file from S3 with expected bucket owner verification."""
    bucket = os.environ.get("INSTALLER_BUCKET")
    if not bucket:
        print("ERROR: INSTALLER_BUCKET not set")
        sys.exit(1)

    expected_bucket_owner = os.environ.get("INSTALLER_BUCKET_EXPECTED_OWNER")
    if not expected_bucket_owner:
        raise ValueError("INSTALLER_BUCKET_EXPECTED_OWNER environment variable is required")
    if not (expected_bucket_owner.isdigit() and len(expected_bucket_owner) == 12):
        raise ValueError("INSTALLER_BUCKET_EXPECTED_OWNER must be a 12-digit AWS Account ID")

    config = Config(read_timeout=300, connect_timeout=60, retries={"max_attempts": 2})
    s3 = boto3.client("s3", config=config)

    print(f"Downloading s3://{bucket}/{s3_path} to {local_path}")
    s3.download_file(
        bucket, s3_path, str(local_path), ExtraArgs={"ExpectedBucketOwner": expected_bucket_owner}
    )


def verify_checksum(file_path, expected_checksum):
    """Verify SHA256 checksum of downloaded file."""
    print(f"Verifying checksum for {file_path}...")
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    actual = sha256.hexdigest()
    if actual != expected_checksum:
        print("ERROR: Checksum mismatch!")
        print(f"  Expected: {expected_checksum}")
        print(f"  Actual:   {actual}")
        sys.exit(1)
    print("OK Checksum verified")


def setup_windows(versions):
    """Install Cinema 4D on Windows for each version."""
    for version in versions:
        install_dir = C4D_INSTALL_PATHS[version]["windows"]
        marker = install_dir / ".installed"

        if marker.exists():
            print(f"Cinema 4D {version} already installed at {install_dir}")
            continue

        print(f"Installing Cinema 4D {version}...")
        installer_info = C4D_INSTALLERS[version]["windows"]
        local_installer = Path(f"C:/Temp/{Path(installer_info['s3_key']).name}")
        local_installer.parent.mkdir(parents=True, exist_ok=True)

        download_from_s3(installer_info["s3_key"], local_installer)
        verify_checksum(local_installer, installer_info["sha256"])

        if installer_info["type"] == "zip":
            extract_dir = Path(f"C:/Temp/c4d_{version}")
            run(
                [
                    "powershell",
                    "-Command",
                    f"Expand-Archive -Path '{local_installer}' -DestinationPath '{extract_dir}' -Force",
                ]
            )
            extracted_c4d = next(extract_dir.glob("*/"), None)
            if extracted_c4d:
                install_dir.parent.mkdir(parents=True, exist_ok=True)
                run(
                    [
                        "powershell",
                        "-Command",
                        f"Move-Item -Path '{extracted_c4d}' -Destination '{install_dir}' -Force",
                    ]
                )
            run(
                ["powershell", "-Command", f"Remove-Item -Path '{extract_dir}' -Recurse -Force"],
                check=False,
            )
        elif installer_info["type"] == "exe":
            print(f"Running installer: {local_installer}")
            result = subprocess.run(
                [
                    str(local_installer),
                    "--mode",
                    "unattended",
                    "--unattendedmodeui",
                    "none",
                    "--prefix",
                    str(install_dir),
                ],
                capture_output=True,
                text=True,
            )
            print(f"Installer exit code: {result.returncode}")
            print(f"Installer stdout: {result.stdout}")
            print(f"Installer stderr: {result.stderr}")

        local_installer.unlink(missing_ok=True)

        if install_dir.exists():
            print(f"SUCCESS: Cinema 4D {version} installed at {install_dir}")
            marker.touch()
        else:
            print(f"ERROR: Cinema 4D {version} not found at {install_dir}")
            run(
                [
                    "powershell",
                    "-Command",
                    "Get-ChildItem 'C:\\Program Files' | Where-Object { $_.Name -like '*Cinema*' -or $_.Name -like '*Maxon*' }",
                ],
                check=False,
            )
            sys.exit(1)

    _configure_rlm_licensing(versions, "windows")


def setup_macos(versions):
    """Install Cinema 4D on macOS for each version."""
    for version in versions:
        install_dir = C4D_INSTALL_PATHS[version]["macos"]
        marker = install_dir / ".installed"

        if marker.exists():
            print(f"Cinema 4D {version} already installed at {install_dir}")
            continue

        if "macos" not in C4D_INSTALLERS.get(version, {}):
            print(f"ERROR: No macOS installer configured for version {version}")
            sys.exit(1)

        print(f"Installing Cinema 4D {version}...")
        installer_info = C4D_INSTALLERS[version]["macos"]
        local_installer = Path(f"/tmp/{Path(installer_info['s3_key']).name}")

        download_from_s3(installer_info["s3_key"], local_installer)
        verify_checksum(local_installer, installer_info["sha256"])

        # Mount the DMG
        mount_point = Path("/tmp/c4d_mount")
        mount_point.mkdir(exist_ok=True)
        run(
            [
                "hdiutil",
                "attach",
                str(local_installer),
                "-mountpoint",
                str(mount_point),
                "-nobrowse",
            ]
        )

        # Find the installer .app inside the DMG
        installer_app = None
        for item in mount_point.iterdir():
            if item.suffix == ".app":
                installer_app = item
                break

        if not installer_app:
            print(f"ERROR: No .app found in DMG. Contents: {list(mount_point.iterdir())}")
            run(["hdiutil", "detach", str(mount_point)], check=False)
            sys.exit(1)

        # Per Maxon docs: copy the .app out of the DMG before running it
        local_app = Path(f"/tmp/{installer_app.name}")
        run(["cp", "-R", str(installer_app), str(local_app)])

        # The InstallBuilder executable is at Contents/macOS/installbuilder.sh
        installer_bin = local_app / "Contents" / "macOS" / "installbuilder.sh"
        if not installer_bin.exists():
            # Fallback: try Contents/MacOS/installbuilder.sh (case variation)
            installer_bin = local_app / "Contents" / "MacOS" / "installbuilder.sh"
        if not installer_bin.exists():
            macos_dir = local_app / "Contents" / "MacOS"
            if not macos_dir.exists():
                macos_dir = local_app / "Contents" / "macOS"
            print(
                f"ERROR: installbuilder.sh not found. Contents of {macos_dir}: {list(macos_dir.iterdir()) if macos_dir.exists() else 'dir missing'}"
            )
            run(["hdiutil", "detach", str(mount_point)], check=False)
            sys.exit(1)

        print(f"Running installer: {installer_bin}")
        result = subprocess.run(
            [
                "sudo",
                str(installer_bin),
                "--mode",
                "unattended",
                "--unattendedmodeui",
                "none",
                "--prefix",
                str(install_dir),
            ],
            stdin=subprocess.DEVNULL,
            timeout=600,
        )
        print(f"Installer exit code: {result.returncode}")

        # Clean up the copied installer app
        run(["rm", "-rf", str(local_app)], check=False)

        run(["hdiutil", "detach", str(mount_point)], check=False)
        local_installer.unlink(missing_ok=True)

        if install_dir.exists():
            print(f"SUCCESS: Cinema 4D {version} installed at {install_dir}")
            run(["sudo", "touch", str(marker)])
        else:
            print(f"ERROR: Cinema 4D {version} not found at {install_dir}")
            run(["ls", "-la", "/Applications/"], check=False)
            sys.exit(1)

    _configure_rlm_licensing(versions, "macos")


def _configure_rlm_licensing(versions, platform_key):
    """Configure Cinema 4D to use RLM licensing without interactive GUI login."""
    license_dns = os.environ.get("LICENSE_ENDPOINT_DNS", "")
    if not license_dns:
        print(
            "WARNING: LICENSE_ENDPOINT_DNS is not set. Skipping licensing config. The test will likely fail."
        )
        return

    license_port = os.environ.get("C4D_LICENSE_PORT")
    if not license_port:
        print("WARNING: C4D_LICENSE_PORT is not set. Skipping licensing config.")
        return

    rlm_config = f"{license_dns}:{license_port}"
    for version in versions:
        install_dir = C4D_INSTALL_PATHS[version][platform_key]
        config_txt = install_dir / "resource" / "config.txt"
        if not config_txt.exists():
            print(f"WARNING: config.txt not found at {config_txt}")
            continue
        content = config_txt.read_text()
        lines = [
            line
            for line in content.splitlines()
            if "g_licenseServerRLM" not in line
            and "g_licenseServerURL" not in line
            and "g_licenseModel" not in line
        ]
        lines.append(f"g_licenseServerRLM={rlm_config}")
        lines.append(f"g_licenseServerURL={rlm_config}")
        lines.append("g_licenseModel=LICENSEMODEL::RLM")
        new_content = "\n".join(lines) + "\n"
        if platform_key == "macos":
            # The macOS install dir is owned by root (installed via sudo), so we
            # write to a temp file first then sudo cp it into place.
            import tempfile

            tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt")
            tmp.write(new_content)
            tmp.close()
            run(["sudo", "cp", tmp.name, str(config_txt)])
            os.unlink(tmp.name)
        else:
            config_txt.write_text(new_content)
        print(f"Configured RLM licensing ({rlm_config}) in {config_txt}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup Cinema 4D test environment")
    parser.add_argument(
        "--versions",
        nargs="+",
        required=True,
        help="Cinema 4D versions to install (e.g., 2025 2026)",
    )
    args = parser.parse_args()

    system = platform.system()
    print(f"Setting up {system} with Cinema 4D {', '.join(args.versions)}")

    for v in args.versions:
        if v not in C4D_INSTALLERS:
            print(f"ERROR: Unsupported version {v}. Supported: {list(C4D_INSTALLERS.keys())}")
            sys.exit(1)

    if system == "Windows":
        setup_windows(args.versions)
    elif system == "Darwin":
        setup_macos(args.versions)
    else:
        print(f"Unsupported platform: {system}")
        sys.exit(1)

    print("Setup complete!")
