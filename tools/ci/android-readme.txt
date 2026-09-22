SimpleChess -- Android arm64 build
==================================

Files
  simplechess            the engine (UCI protocol), 64-bit Arm, fully static, position-independent
  SCNNUEv*.scn5          the neural network the engine plays with -- REQUIRED, the engine exits without it
  README-ANDROID.txt     this file

Which archive
  ...-android-arm64          any phone SoC from about 2018 on (Cortex-A75/A55 and newer, i.e. anything
                             with the Arm dot-product extension). This is the build to use.
  ...-android-arm64-generic  older 64-bit SoCs without dot-product (2016-2017 era). Same engine, but its
                             int8 network layers run as scalar code, so it is much slower. Use it only
                             if the arm64 build does not start on your device.

Install in DroidFish
  1. Copy BOTH `simplechess` and the `.scn5` file into DroidFish's engine folder
     (by default DroidFish/uci on internal storage, i.e. /storage/emulated/0/DroidFish/uci).
  2. In DroidFish, Settings > Engine settings > pick `simplechess`.
  3. The engine looks for the net beside its binary and in a `nets/` subfolder. If it still
     reports "no NNUE net could be loaded", open the engine's UCI options in DroidFish and set
     EvalFile to the net's full path, e.g. /storage/emulated/0/DroidFish/uci/SCNNUEv3-2026-09-12.scn5
  Any other UCI front-end: same idea -- keep the net beside the binary, or point EvalFile at it.

Notes
  Built by the repository's GitHub Actions workflow (.github/workflows/android.yml) from the
  tagged source: a plain LTO build, no profile-guided optimisation and no per-SoC tuning, so it
  runs somewhat below a native tuned build. The front-end sets Hash and Threads; the engine's
  compiled-in defaults assume a desktop.
  Source and license (GPL-3.0): https://github.com/LinkLikesLattes/SimpleChess
