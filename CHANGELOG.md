# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [PEP 440](https://www.python.org/dev/peps/pep-0440/) 
and uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.4]
### Added
- Add `mypy` to [`static-analysis`](.github/workflows/static-analysis.yml)

### Fixed
- Decimal values in our API responses have been incorrectly serialized as strings rather than numbers since at least [v0.1.0](https://github.com/ASFHyP3/hyp3-event-monitoring/pull/79), which broke our custom JSON encoder by pinning to `flask==3.0.3` (`flask` was previously unpinned). The `json_encoder` app attribute was removed in [Flask v2.3.0](https://github.com/pallets/flask/blob/main/CHANGES.rst#version-230). This release fixes this issue by subclassing `flask.json.provider.JSONProvider`. Also see https://github.com/pallets/flask/pull/4692 and [HyP3 v9.0.0](https://github.com/ASFHyP3/hyp3/releases/tag/v9.0.0).

## [0.1.3]
### Changed
- The [`static-analysis`](.github/workflows/static-analysis.yml) Github Actions workflow now uses `ruff` rather than `flake8` for linting.

## [0.1.2]
### Fixed
- Upgraded to flask-cors v5.0.0 from v4.0.1. Resolves [CVE-2024-6221](https://www.cve.org/CVERecord?id=CVE-2024-6221).

## [0.1.1]
### Changed
- Upgrade the API Lambda runtime from Python 3.8 to 3.12. This Python version pin was overlooked during the previous release.

## [0.1.0]
### Removed
- Support for Python 3.8 has been removed. Python 3.12 is now supported.

## [0.0.13]
### Changed
- `harvest_products` Lambda function now harvests data products via download and upload, rather than S3 copy.

## [0.0.12]
### Fixed
- Handle the case where a product has no temporal neighbors.

## [0.0.11]
### Added
- Added CORS support to product bucket in order to support Vertex's "Download All" feature.

## [0.0.10]
### Fixed
- Replaced deprecated `hyp3_sdk.asf_search.get_nearest_neighbors` function with `find_new.get_neighbors`.

## [0.0.9]
### Security
- Set `NoEcho` for EDL password in CloudFormation stacks.

## [0.0.8](https://github.com/ASFHyP3/hyp3-event-monitoring/compare/v0.0.7...v0.0.8)
### Changed
- Granted additional IAM permissions to the `harvest_products` Lambda function to support transfers of data products
  smaller than 8 MB.

## [0.0.7](https://github.com/ASFHyP3/hyp3-event-monitoring/compare/v0.0.6...v0.0.7)
### Changed
- Upgraded to hyp3_sdk [v1.3.2](https://github.com/ASFHyP3/hyp3-sdk/blob/develop/CHANGELOG.md#132) from v1.1.0
  - InSAR jobs are now submitted using the custom `apply_water_mask=True` setting added in hyp3_sdk v1.3.2

## [0.0.6](https://github.com/ASFHyP3/hyp3-event-monitoring/compare/v0.0.5...v0.0.6)
### Changed
- Upgraded to hyp3_sdk [v1.1.0](https://github.com/ASFHyP3/hyp3-sdk/blob/develop/CHANGELOG.md#110) from v0.6.0
  - RTC jobs are now submitted using the default `dem_name='copernicus'` setting added in hyp3_sdk v1.1.0

## [0.0.5](https://github.com/ASFHyP3/hyp3-event-monitoring/compare/v0.0.4...v0.0.5)
### Changed
- Improved handling of transient server errors (retryable) vs invalid granule errors (not retryable) in `find_new`
- Upgraded to hyp3_sdk [v0.6.0](https://github.com/ASFHyP3/hyp3-sdk/blob/develop/CHANGELOG.md#060) from v0.5.0

## [0.0.4](https://github.com/ASFHyP3/hyp3-event-monitoring/compare/v0.0.3...v0.0.4)
### Added
- New IAM role that can be assumed by external AWS accounts to manage records in the Events table.

## [0.0.3](https://github.com/ASFHyP3/hyp3-event-monitoring/compare/v0.0.2...v0.0.3)
### Changed
- Check for new granules is now run every 30 minutes instead of every hour.

## [0.0.2](https://github.com/ASFHyP3/hyp3-event-monitoring/compare/v0.0.1...v0.0.2)
### Changed
- Error handling for baseline api calls now skip on 500 errors and record 400 errors so that we retry when necessary.

## [0.0.1](https://github.com/ASFHyP3/hyp3-event-monitoring/compare/v0.0.0...v0.0.1)

Initial release.
