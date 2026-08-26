
import os
import glob
import prophet

prophet_dir = os.path.dirname(prophet.__file__)

tbb_file = glob.glob(
    os.path.join(
        prophet_dir,
        "stan_model",
        "cmdstan-*",
        "**",
        "tbb.dll"
    ),
    recursive=True
)[0]

tbb_dir = os.path.dirname(tbb_file)

os.environ["PATH"] = tbb_dir + os.pathsep + os.environ["PATH"]
dll_handle = os.add_dll_directory(tbb_dir)
