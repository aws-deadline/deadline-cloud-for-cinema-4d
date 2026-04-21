#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Setup runner for Cinema 4D integration tests in CodeBuild."""

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
        "linux": {
            "s3_key": "cinema4d/2025/Cinema4D_2025_2025.3.1_Linux.zip",
            "sha256": "40b4a85d38dcdf5fa19fa19b03efde6494fe3e482b96836d5b736956133ff98f",
            "type": "zip",
        },
    },
    "2026": {
        "windows": {
            "s3_key": "cinema4d/2026/Cinema4D_2026_2026.0_Win.exe",
            "sha256": "412b069a00b39564aaaa7c1ccfa080d9e154669028e3521b96282c4dfcfd4024",
            "type": "exe",
        },
        "linux": {
            "s3_key": "cinema4d/2025/Cinema4D_2025_2025.3.1_Linux.zip",
            "sha256": "40b4a85d38dcdf5fa19fa19b03efde6494fe3e482b96836d5b736956133ff98f",
            "type": "zip",
        },
    },
}

C4D_INSTALL_PATHS = {
    "2025": {
        "windows": Path("C:/Program Files/Maxon Cinema 4D 2025"),
        "linux": Path("/opt/maxon/cinema4d-2025"),
    },
    "2026": {
        "windows": Path("C:/Program Files/Maxon Cinema 4D 2026"),
        "linux": Path("/opt/maxon/cinema4d-2026"),
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
            # The zip contains a cinema4d subfolder — move it to install path
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

    _configure_rlm_licensing(versions)


def _configure_rlm_licensing(versions):
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
        install_dir = C4D_INSTALL_PATHS[version]["windows"]
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
        config_txt.write_text("\n".join(lines) + "\n")
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
    else:
        print(f"Unsupported platform: {system}")
        sys.exit(1)

    print("Setup complete!")
