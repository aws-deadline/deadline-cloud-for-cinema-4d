## 0.6.1 (2025-01-13)



### Bug Fixes
* initialize connection to Maxon assets DB on Windows to fix confusing error message (#144) ([`f75b68d`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/f75b68d00ea029723fe573df40b3b78b3adf92fd))
* Add error logs for Redshift. (#143) ([`46771f3`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/46771f333f4c70acc1dfe362a5da55bc321b4e13))
* Refactor redshift non-ascii test. (#141) ([`0691c44`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/0691c444df7576a4256c7662e6e6c8b48e1f8ea1))

## 0.6.0 (2025-01-03)


### Features
* Implement asset path mapping for Cinema 4D scene files (#126) ([`33ac2e8`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/33ac2e8c298ac7902b1bdc1c5db87397816e1228))
* **adaptor**: Update adaptor environment variable executable to C4D_COMMANDLINE_EXE (#121) ([`206b0ad`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/206b0add6bd93ab2587508a075b350e53f1f69f1))

### Bug Fixes
* Fix adaptor packaging script to package dependencies. (#137) ([`b130ccc`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/b130cccfba780a5ac540a118feb38c316790c45b))
* Tighten error regex pattern. (#136) ([`83f0a3c`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/83f0a3c59414fc2c7f440582fdadccb1501b2f4a))
* Ensure stdout/err streams are unbuffered. (#134) ([`0b3c05d`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/0b3c05d5c724c63c3a735698e31834b91dbb55e8))
* add path mapping rules to convert Windows paths to C4D's Linux path format (#127) ([`8fc40d9`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/8fc40d9cbbd87a9da593d96b11b0d2bf4b6cc406))

## 0.5.4 (2024-11-26)



### Bug Fixes
* use description from GUI submitter (#115) ([`afe039b`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/afe039b52430abe9c8e2ecddc9bda97466ac8f81))

## 0.5.3 (2024-11-22)



### Bug Fixes
* use user configured installdir for C4D submitter location (#113) ([`173297a`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/173297a4918c87386cf7e16b6fa1aa7817239294))

## 0.5.2 (2024-11-21)



### Bug Fixes
* install C4D plugin into user directory to avoid needing elevated permissions (#110) ([`572696c`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/572696cfec82ffcf9acf2e2e80c29c8a2915fc69))

## 0.5.1 (2024-11-20)



### Bug Fixes
* correct OS conditional for Windows paths (#104) ([`748e1f7`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/748e1f7e24669112f3d9902508aebb12872e036a))

## 0.5.0 (2024-11-20)

### BREAKING CHANGES
* This release contains two breaking changes

### Features
* install Conda packages by default (#96) ([`8ad8986`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/8ad8986c6bb073cb572b176b87e85cecd6b091b4))

### Bug Fixes
* use only Windows workers by default (#100) ([`88bd6a5`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/88bd6a5c14aa0996ed04cfff452b925d44d17f1c))

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

