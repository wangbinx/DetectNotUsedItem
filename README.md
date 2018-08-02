usage: DetectNotUsedItem [-h] [-i] [--dirs] [--clean] [--log]

Detect unreferenced PCD and GUID/Protocols/PPIs. Copyright (c) 2018, Intel
Corporation. All rights reserved.

optional arguments:

  -h,  --help             show this help message and exit
  
  -i , --input            Input DEC file name.
  
  --dirs                  The package directory. To specify more directories, please
                          repeat this option.
						  
  --clean                 Clean the unreferenced items from DEC file.
  --log                   Put log in specified file as well as on console.