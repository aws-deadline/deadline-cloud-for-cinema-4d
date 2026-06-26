# Frequently Asked Questions

## Custom plugins

### Can I deliver my own Cinema 4D plugins to Deadline Cloud workers?

Yes. The `cinema4d` conda package includes a customer plugin hook that downloads custom plugins from your Job Attachments S3 bucket onto the worker at session start, and registers them with Cinema 4D through `g_additionalModulePath`. Upload your plugin folders to a structured S3 path and they are picked up automatically by Cinema 4D when the job runs.

The customer plugin hook is currently supported on:

| Cinema 4D version | Linux | Windows |
|-------------------|-------|---------|
| 2024              | n/a¹  | not yet² |
| 2025              | ✅    | ✅      |
| 2026              | ✅    | ✅      |

¹ Cinema 4D 2024 is only supported on Windows by Deadline Cloud.
² Customer plugin hook support for Cinema 4D 2024 on Windows is planned and will be added once verified.

See the [Custom plugins section of the README](../README.md#custom-plugins) for the exact S3 paths and an upload example.

### Why isn't my plugin loading on Cinema 4D 2024?

The customer plugin hook is only verified and shipped for Cinema 4D 2025 and 2026 on both Linux and Windows. If you need custom plugins on Cinema 4D 2024, upgrade to 2025 or 2026 on your fleet, or build your own conda package that installs an activate.d hook to set `g_additionalModulePath` to your plugin directory.

### Where on the worker are the custom plugins stored?

Plugins are downloaded into `${OPENJD_SESSION_WORKING_DIR}/deadline-plugins/cinema4d` for the duration of the session, and the directory is prepended to `g_additionalModulePath` so Cinema 4D loads them at startup. The directory is cleaned up automatically when the session ends.

### What happens if I have no plugins in the S3 prefix?

The customer plugin hook is a no-op when no plugins are found at the expected S3 paths. It is safe to leave the feature enabled even if you don't use custom plugins.
