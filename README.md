# IBOOTPY
A simple tool that to replace the perl script provided with first generation iboot devices.  Has been tested with an iBoot G2 and demonstrated to work.

## Installation
In a virtual env, anaconda env, or other Python 3.x install you can simply run `python setup.py install`.

This will add a iboot module to the site-packages as well as an ibootpy binary to the path

### Files Created
 * ibootpy - located in python environments 'bin' directory.
 * iboot-0.1.0-py<ver>.egg - located (for anaconda) inside the environments lib/pythonX/site-packages/ folder.


## Inspiration
During an expansion of our lab management infrastructure we discovered the older perl script no longer functioned due to the move to the DxP protocol on newer devices. Fortunately the basic infrastructure for making DxP work via python existed, since the provided C libraries rely on winsock and are windows only.  This expands the original library to provide a full tool for ease of use.

## Usage
This update provides a basic command-line tool for using the DxP protocol allowing status checks, toggling relays, and setting all relays to on or off. It can be run using the command `ibootpy`.

```
ibootpy [-h] [--port PORT] [-v] [-q] [--debug] IP USER PASSWORD ACTION

ibootpy - iBoot DxP Tool

positional arguments:
  IP             IP you wish to interact with
  USER           User Name
  PASSWORD       Device Password
  ACTION         Action to perform on list of iBoot Devices (default status)

optional arguments:
  -h, --help     show this help message and exit
  --port PORT    Port to communicate with device
  -v, --verbose  verbose output
  -q, --quiet    silence output, simply return success or failure.
  --debug        Enable Debug Output

```

## Alterations From Base Package

### Python Version
This module is now adjusted to be compliant with Python 3.

### Get Relays
This now returns a dictionary of the relays correctly formatted for toggling and setting updates by updating the individual relay entries and feeding the dictionary back to the interface.

### Logging
No longer institutes default DEBUG output, simply provides a logger called 'iBootInterface', when running ibootpy this defaults to INFO level output with flags to enable DEBUG or silence all output.

### iBootDevice Interface Setup
The interface will now directly accept strings for username and password instead of requiring you to use str.encode() on them.  It does this by simply checking for string types and converting them during `__init__` of the interface.

### Normalization of Indexing
I've tried to step through the system and make sure that ranges are used the same everywhere, the relays are 1 indexed (this is not documented in the protocol sheet) so I've tried to make sure all indexing is done correctly vs. a 1 index instead of having to manipulate relay numbers mid code.

## Future Work
 * Properly formatted output instead of relying solely on log output.
  * This may actually be easiest to do with a second logger that just handles formatted standard output, this would allow quiet to work relatively trivially.
 * Refactoring of seq_num updates to easily readable code paths. There's updates in some odd places, they work but they make following code flow difficult.
