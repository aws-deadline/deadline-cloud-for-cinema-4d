## 0.4.1 (2024-11-13)



### Bug Fixes
* install pip if required before installing GUI dependencies (#91) ([`4b5b75a`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/4b5b75af991c94f033bae84ceb061d4d0f1a278a))

## 0.4.0 (2024-11-13)

### BREAKING CHANGES
* renamed env variable for loading adaptor executable, added support for running the adaptor on Linux, and added support for earlier versions of 2024 (#59) ([`be33b63`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/be33b63860a2d078f2802766d6eb5ce567c05aba))
* add adaptor output path mapping and overrides (#55) (#73) ([`6dcaf4a`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/6dcaf4a35dfb6704bdb4c04b78e76e2e36a43349))

### Features
* Add InstallBuilder submitter installer XML. (#85) ([`73dbb75`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/73dbb7518c04b8d443849f57e9461b4cf14c4d2e))
* Only import openjd and deadline modules. (#88) ([`71911ae`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/71911ae1394203fea36875b1350e4cb4a67470d1))
* prompt save before submit (#53) (#69) ([`c1d463c`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/c1d463c6c57fdd95c2a3d4e58d024ba3ad58a693))
* Add DeadlineCloudSubmitter plugin ID to submitter plugin. ([`9242593`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/9242593455c70ce06cacec94d84839bf957a47cc))

### Bug Fixes
* Resolve typos in bundling scripts. (#82) ([`caf33e3`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/caf33e3ac3136c311c18069c2fa78628fcddbcfc))
* Ensure only Critical stops fail the job and not others. (#80) ([`80af90f`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/80af90fbf2fe75c4866b26abc8cea5ba66f974ef))
* Fix python-semantic-release issues with 9.12 (#78) ([`8cc9728`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/8cc9728c52e2e6ea83b2871887299f01124889ff))
* handle CRITICAL error in adaptor regex callbacks (#51) (#72) ([`817eb68`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/817eb68346f165de974dca55033837a07548884b))
* adaptor handle render result failure results (#66) (#76) ([`8e0e127`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/8e0e1277dd15faa0a8784c95b0fcb43b0505236d))
* Add path mapping to outputs (#57) ([`056f5ea`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/056f5ea931b78eea0e21024e192179c7f5d871d8))

## 0.3.4 (2024-06-27)



### Bug Fixes
* frame override checkbox with pyside6 (#54) ([`9f3813c`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/9f3813c65451f073cea4d256817dd2f927b906c0))

## 0.3.3 (2024-06-19)



### Bug Fixes
* properly access multipass filename from render data (#47) ([`6da82bf`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/6da82bf511b4af364b047fd22f678c63230acf92))
* windows adaptor was failing to load (#44) ([`f5b1c6d`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/f5b1c6d76c40811a78cd14cd822872fd47f93488))

## 0.3.2 (2024-05-08)



### Bug Fixes
* update imports (#36) ([`ef50e5a`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/ef50e5ae7745addcb601b7dc7d91304a4d307dff))

## 0.3.1 (2024-05-01)

### Dependencies
* update deadline requirement from ==0.47.* to ==0.48.* (#33) ([`8e16c43`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/8e16c437872e81162a79ba2c220397cc180deddb))


## 0.3.0 (2024-04-02)

### BREAKING CHANGES
* public release (#21) ([`2fc84af`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/2fc84affe0206687d08915c8301f0cbd8882f075))



## 0.2.1 (2024-03-26)

### Dependencies
* update deadline-cloud dependency 0.45.0 (#15) ([`3677a7b`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/pull/15/commits/3677a7b7e1e73939ecae6987fbdc4bc4842c38ec))

## v0.2.0 (2024-03-15)

### Breaking
* change project naming from ...cinema4d -&gt; ...cinema-4d (#8) ([`676cbab`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/676cbab3b6fb10054d4e9c987c137aa40736921f))

## v0.1.0 (2024-03-15)

### Breaking
* init integration commit (#1) ([`0cd4e1c`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/0cd4e1ccab0398090e3878f9c27123acf00748df))

### Chore
* update deps deadline-cloud 0.40 (#6) ([`479adab`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/479adab182a2072d002ad960e1e32c91cf3dfa07))

