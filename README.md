# Basic Aioquic Examples

This repository provides examples of how to use the [aioquic](https://github.com/aiortc/aioquic) library, a Python implementation of the QUIC transport protocol. The examples demonstrate:

*   **Fundamental Client/Server Interaction:** `Basic_aioquic_client.py` and `Basic_aioquic_server.py` offer simplified implementations to illustrate the core concepts of setting up a QUIC client and server.
*   **Data Transfer:** `client.py` and `server.py` showcase a more practical scenario of sending random bytes of data over a QUIC connection.

The goal is to help users understand the basics of `aioquic` and provide a starting point for building more complex QUIC-based applications.

## File Descriptions

*   `Basic_aioquic_server.py`: A minimal server example. It demonstrates the fundamental steps to set up a QUIC server that can listen for incoming connections. This script is primarily for educational purposes to understand `aioquic` server basics.
*   `Basic_aioquic_client.py`: A minimal client example. It shows the essential steps to create a QUIC client that can connect to the `Basic_aioquic_server.py`. This script is also for educational purposes.
*   `server.py`: A more advanced server example that handles multiple client connections and is designed to receive random bytes of data from `client.py`.
*   `client.py`: A more advanced client example that connects to `server.py` and sends a stream of random bytes, demonstrating data transfer over QUIC.

## Dependencies

To run these examples, you'll need Python 3.7 or newer. The primary dependency is `aioquic` and `numpy`. You can install them using pip:

```bash
pip install aioquic numpy
```

## Usage

You'll need two terminal windows to run the server and client scripts.

**Note on Certificates:** The server scripts (`Basic_aioquic_server.py` and `server.py`) require a TLS certificate and a private key. You can generate a self-signed certificate for testing purposes using OpenSSL:

```bash
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
```
This will create `cert.pem` (certificate) and `key.pem` (private key) in your current directory.

### 1. Basic Examples

These examples demonstrate a minimal QUIC connection. The server and client in these basic examples default to using the IP address `172.16.2.1` and port `9999`. Ensure this address is appropriate for your local setup, or modify the scripts if you wish to use `localhost`.

**Terminal 1: Start the Basic Server**
```bash
python Basic_aioquic_server.py -c cert.pem -k key.pem
```
*   The server will listen on `172.16.2.1:9999` by default.
*   `-c CERTFILE`: Path to the TLS certificate file (e.g., `cert.pem`).
*   `-k KEYFILE`: Path to the TLS private key file (e.g., `key.pem`).

**Terminal 2: Run the Basic Client**
```bash
python Basic_aioquic_client.py
```
*   The client will attempt to connect to `172.16.2.1:9999` by default.
You can also specify the transfer size (in MiB, defaults to 64):
```bash
python Basic_aioquic_client.py 128
```

### 2. Data Transfer Examples

These examples demonstrate sending random bytes of data over QUIC.

**Terminal 1: Start the Data Transfer Server**
```bash
python server.py -c cert.pem -k key.pem
```
*   `--host HOST`: The address to listen on (default: `::`).
*   `--port PORT`: The port to listen on (default: `4433`).
*   `-c CERTIFICATE`: Path to the TLS certificate file (required).
*   `-k PRIVATE_KEY`: Path to the TLS private key file.
*   Other options like `--quic-log`, `--secrets-log`, `-v` (verbose) are also available. Use `python server.py --help` for details.

**Terminal 2: Run the Data Transfer Client**
```bash
python client.py --host localhost --port 4433
```
*   `--host HOST`: The server's host name or IP address (default: `localhost`).
*   `--port PORT`: The server's port number (default: `4433`).
*   `--querysize BYTES`: Amount of data to send in each query (default: `5000`).
*   `--streamrange COUNT`: Number of times to send `querysize` data (default: `100`).
*   `-k` or `--insecure`: Do not validate server certificate (useful for self-signed certs).
*   Other options like `--ca-certs`, `--quic-log`, `--secrets-log`, `-v` (verbose), `--maxdata`, `--maxstreamdata` are also available. Use `python client.py --help` for details. Remember to use the `-k` (or `--insecure`) flag if you are using a self-signed certificate on the server.
