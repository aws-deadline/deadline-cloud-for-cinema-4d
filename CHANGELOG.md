## 0.9.1 (2025-12-18)


### Features
* add release date to submitter "about" panel (#366) ([`152ee96`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/152ee9686bdfff5e701e63a130c7951db43c5eb8))
* Add the 'About' panel for the submitter. (#364) ([`5999dde`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/5999dde8c06c703fc48abf52f9bc742520ae0d1b))

### Bug Fixes
* replace value in path and add warning for missing for multiple… (#365) ([`a303664`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/a3036647b1a4f48e689409a47ef20663960a7af6))
* do not pathmap Pyro output in C4D 2026 and up (#362) ([`8c79b53`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/8c79b533ff1a9905083bc8c04f8806ad64a7681d))
* Add timeouts for all the steps and not just the first take. (#360) ([`2b55041`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/2b55041797d13fcdc6e35445fbaf875148a6d314))


## 0.9.0 (2025-12-04)


### Features
* Print the submitter version in the logs. (#358) ([`3df12a0`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/3df12a08f74206b7b8f2bab6b1da18893e8a397d))
* Add Cinema 4D detailed debug logs. (#349) ([`8561129`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/8561129c5a399c782c69f800f04daa6916bcd7e3))
* Add cross-platform font support (#345) ([`2f65b2e`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/2f65b2e18938d0164de1ab95ed9f98b59f7d1802))

### Bug Fixes
* Exclude Maxon DB assets from job bundle references (#353) ([`626ecbf`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/626ecbf2e9919214c574c16dab1747c35fe30a4a))
* Add validation to detect pipe characters in asset paths (#348) ([`abe0c0c`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/abe0c0cc7d0ffd61bfeec79ae3d6aada864c7722))


## 0.8.5 (2025-11-19)


### Features
* Add detailed Cinema 4D + Redshift logging option while submitting (#342) ([`64e82a8`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/64e82a80486cfa3d88d501aab3969398b55af17f))



## 0.8.4 (2025-11-04)


### Features
* add submitter support for Cinema 4D to Arnold (#330) ([`dd56f41`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/dd56f411ec08590d305286131b6fa517a93bbe18))

### Bug Fixes
* Allow other users to access dependencies installed by system installation (#324) ([`5a0f997`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/5a0f997459093b46070e4f604ca9dd05c69d9f56))


## 0.8.3 (2025-11-04)


### Features
* Include fonttools in submitter installer. (#306) ([`2422e7f`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/2422e7f8000d8840933b821a58667837863cc7f1))

### Bug Fixes
* Silently log errors and continue font handling. (#326) ([`21a46da`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/21a46dad593a28c78802bbe57283c5ffa420c376))
* Only bundle fonts on Windows as its not supported on Mac. (#294) ([`6ecebce`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/6ecebce5fc2dbf98e048adfd193511488d835dca))


## 0.8.2 (2025-08-12)


### Features
* improved render progress reporting (#287) ([`d6ab2c0`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/d6ab2c034b0c7a22d00c4cb2b41c728760808c75))
* Implement font handling for Cinema 4D submitter for Windows. (#283) ([`f4e4b17`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/f4e4b17054a4c3f69c38c1b67f31a46070bb6eae))

### Bug Fixes
* Use scene file location to map path for fonts folder. (#286) ([`bb77b8f`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/bb77b8f20c8627ab020552cde91ce6b2b272b302))
* Add the known asset root paths to suppress job submission warnings. (#284) ([`350ba4f`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/350ba4ff9014ae3448857f5f1a58773b607f7e8e))

## 0.8.1 (2025-08-07)

### Bug Fixes
* use blackslashes for Windows paths in submitter installer (#275) ([`3d39370`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/3d393707a7526258325f286b02b6c04a508d5a52))
* upgrade deadline version to fix bug where submitter stays open after submission (#276) ([`398cd7e`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/398cd7e5b3c9f1209bd6b6ddbacbf3fc84288043))

## 0.8.0 (2025-07-31)

### BREAKING CHANGES
* Allow deactivating automatic error checking in Cinema4D jobs (#244) ([`1421f72`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/1421f72222472eb43d9d21ba9034d686e7789913))
* Allow deactivating error checking in the Cinema4D adaptor (#245) ([`8137c8f`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/8137c8faa290992b8ec1010368020fa6ab79b4dd))

The init-data schema has changed to support the option to deactivate automatic error checking in the adaptor. If you use Deadline Cloud customer managed fleets, you will need to update your adaptor on the worker before using the latest submitter. The Deadline Cloud service team handles adaptor upgrades on service managed fleets.

### Features
* Remember last used shared job settings for job submissions (#235) ([`577377a`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/577377a42a32c025268d041715d117565f067d37))

### Bug Fixes
* Change allowedValues order to match the openjd checkbox specifications (#264) ([`ecbe927`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/ecbe927737081a0cc06d3966e7100059f1596a7e))
* remap assets per session instead of per frame (#261) ([`004746d`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/004746db0f67d8862c0e097dd27513022afbe620))
* Reduce logging for path mapping. (#258) ([`bef03af`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/bef03af9a83d0add11f39f09a3abb8cb463acdb0))
* Save project with assets feature raises exception if all the paths to assets are not found. (#253) ([`85a00eb`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/85a00eba8e2a1164297756010a913d7a52563034))
* Path mapping issues on Linux with save project with assets (#252) ([`67eff55`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/67eff55ea4546c810da64f4bc6d3f8e57e70a7cc))

## 0.7.10 (2025-07-07)


### Features
* Bundle scene and assets before submission. (#243) ([`9a4d11b`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/9a4d11b00a31b2508d03d9b5872263423a1041eb))

### Bug Fixes
* Use the output paths from the scene file instead of the exported scene. (#249) ([`85bb260`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/85bb2609d0721a302d3262aedda46addc5419d3e))

## 0.7.9 (2025-06-26)


### Features
* Remember last used output paths and take selection for job submissions (#231) ([`91302b7`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/91302b7b3539a0f5655b8c7c325f3572abde0de6))

### Bug Fixes
* support all takes flow for multi-take/render setting/frame range jobs (#237) ([`a107abe`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/a107abe534004d5a46bf8d95a360289efffda2d2))

## 0.7.8 (2025-06-16)



### Bug Fixes
* Execute passes for scenes to fix pyro caching issue (#232) ([`aa4f503`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/aa4f503d403e7cedeb2f6887bbaf208931625d83))
* sdist failed to install (#227) ([`662e726`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/662e7264de1010618cfd3cb674d4ea91f22a53a3))

## 0.7.7 (2025-05-23)



### Bug Fixes
* Replace backslashes to frontslashes for Mac to Win submissions. (#222) ([`c87bdcb`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/c87bdcb2db9ae906d8647d46a008bafbe2a8e559))

## 0.7.6 (2025-05-22)



### Bug Fixes
* Add exception handling while opening RS render view. (#219) ([`c134d1a`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/c134d1a47a27dedcd67d8da698eaacc5ccfbb8ef))
* Open RS renderview during Cinema 4D startup (#218) ([`ca6c630`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/ca6c6303cd324afa3170340a48344c5a9cc7d1c0))

## 0.7.5 (2025-05-08)



### Bug Fixes
* support path mapping for RedShift assets (#211) ([`2d9a74b`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/2d9a74bb208de6eba623c36bc407c6facd6b73e7))
* Fix failures with RS RenderView when opening Cinema 4D submitter (#207) ([`f714867`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/f714867772f16b281cccb2b15f49b61c34c57db7))
* Allow Cinema 4D to be rendered on all available machines instead of just windows. (#204) ([`2ab96aa`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/2ab96aadd260cf7b969ce2c068627419324b773d))

## 0.7.4 (2025-04-10)



### Bug Fixes
* Add better messaging when Redshift runs out of memory. (#196) ([`9dbea22`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/9dbea2268f4d70afede758f73b1aedceb0d100dd))

## 0.7.3 (2025-03-31)



### Bug Fixes
* Remove 'CRITICAL: Stop' from error regexes in adaptor (#192) ([`4a959e8`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/4a959e8f26c97fe7558ea23f59514a2694014ae0))

## 0.7.2 (2025-03-27)


### Features
* Add configurable GUI timeouts for jobs in submitter. (#180) ([`2b79232`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/2b79232739b2561de52b5414b60225f5f7ca82ea))

### Bug Fixes
* Avoid checked take from overriding other takes in submission (#185) ([`a015719`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/a015719dc93577fc95c7a584b23cd026bbd87fb9))
* Replace C4D tokens with values in paths. (#183) ([`d655133`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/d6551334e63241941aa2dfa14316b62b1334ba14))
* Add timeout for Cinema 4D jobs on EnvExit. (#173) ([`ce769c0`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/ce769c0168889c81811d575cfe12b54ddc43d76e))

## 0.7.1 (2025-02-05)



### Bug Fixes
* Use RDATA_FRAMESEQUENCE_CUSTOM only if it exists. (#163) ([`7b4fb97`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/7b4fb97021a990d995c42c7e77ac1361981eeab9))

## 0.7.0 (2025-02-03)

**This release has been pulled from PyPI. The use of this release can cause the submitter to fail on Cinema 4D 2024.5.1 version. Downgrade to 0.6.1 or upgrade to the next release if available.**

### BREAKING CHANGES
* handle custom frame ranges (#152) ([`c1b1d38`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/c1b1d38bc850c7cfdf421ae3d7b680fb2d54d9f2))

The function signatures of the `Animation` and `Scene` class member functions have been updated to correctly parse frame ranges from Cinema 4D. If you have scripts that directly call the `Animation` or `Scene` class member functions, the scripts will need to be updated. 


### Features
* prepopulate Windows host requirement (#150) ([`6673b17`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/6673b171f781557be7c47fac9be461098122c204))

### Bug Fixes
* improve error handling for sticky settings having a long path (#148) ([`99e4d53`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/99e4d53a0ff4eb820562756201339aac59ce9b3a))
* Use Path instead of string in output paths in adaptor template. (#147) ([`ab11bdc`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/ab11bdca216e7f1b6be47d31381a565a64a319c9))

## 0.6.1 (2025-01-13)



### Bug Fixes
* initialize connection to Maxon assets DB on Windows to fix confusing error message (#144) ([`f75b68d`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/f75b68d00ea029723fe573df40b3b78b3adf92fd))
* Add error logs for Redshift. (#143) ([`46771f3`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/46771f333f4c70acc1dfe362a5da55bc321b4e13))
* Refactor redshift non-ascii test. (#141) ([`0691c44`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/0691c444df7576a4256c7662e6e6c8b48e1f8ea1))

## 0.6.0 (2025-01-03)

### BREAKING CHANGES
* **adaptor**: Update adaptor environment variable executable to C4D_COMMANDLINE_EXE (#121) ([`206b0ad`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/206b0add6bd93ab2587508a075b350e53f1f69f1))

The environment variable used to find the Cinema 4D executable in the adaptor was changed from `CINEMA4D_ADAPTOR_COMMANDLINE_EXE` to `C4D_COMMANDLINE_EXECUTABLE`. If you were setting the previous variable, you will need to update the environment set up. If you relied on the executable being on the PATH, then no change is required.

### Features
* Implement asset path mapping for Cinema 4D scene files (#126) ([`33ac2e8`](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/commit/33ac2e8c298ac7902b1bdc1c5db87397816e1228))

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

