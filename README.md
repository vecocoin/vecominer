# vecominer
A simple solominer for Veco that requires no mining pools.

## Requirements:
A full node (local or remote) with active rpc server:
`server = 1`
in veco.conf

## Usage:
`VecoMiner.exe [-h] [-u USERNAME] [-p PASSWORD] [–host HOST] [–port PORT] -a ADDRESS [-s {0,1}] [-t THREADS] [-i ITERATIONS]`

### VECO CLI Miner

#### Arguments:
```
-h, –help                              show this help message and exit
-u USERNAME, –username USERNAME        RPC username (default: none)
-p PASSWORD, –password  PASSWORD       RPC password (default: none)
–host HOST                             RPC server host (default: 127.0.0.1)
–port PORT                             RPC server port (default: 26920)
-a ADDRESS, –address ADDRESS           wallet address to receive mined blocks (required)
-s {0,1}, –ssl {0,1}                   use SSL (1 = HTTPS, 0 = HTTP, default: 0)
-t THREADS, –threads THREADS           number of mining threads (default: max cores)
-i ITERATIONS, –iterations ITERATIONS  iterations per request (default: auto-calibration for 30s duty cycles)
```

## Examples:
If you mine on the same PC that you run your node on, the default settings work well and the command is simply:

`VecoMiner.exe -a VR3sYurX7fG865MjuptiqoHrM2fHWE8n9s -t 4`

If you mine on a remote server (e.g. "mynode.com") that uses ssl, a different port, and password + username:

`VecoMiner.exe -a <address> -h mynode.com -u <username> -p <password> -p <port> -s 1`
