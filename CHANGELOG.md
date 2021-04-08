# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [PEP 440](https://www.python.org/dev/peps/pep-0440/) 
and uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
