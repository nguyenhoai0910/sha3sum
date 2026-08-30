#!/usr/bin/env python3
import hashlib
import sys
import argparse
from colorama import init, Fore
init(autoreset=True)

def hash_file(file_path, algo, chunk_size=65536):
    h = hashlib.new(algo)
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()

def main():
    parser = argparse.ArgumentParser(description="Compute SHA3/BLAKE2 hash of a file")
    parser.add_argument("file", help="Path to file")
    parser.add_argument("-a", "--algo", default="sha3_256",
                         choices=["sha3_256", "sha3_512", "blake2b", "blake2s"])
    parser.add_argument("-c", "--compare", help="Hash string to compare against")
    args = parser.parse_args()

    computed = hash_file(args.file, args.algo)

    if args.compare:
        match = computed.lower() == args.compare.strip().lower()
        status = "MATCH" if match else "NO MATCH"
        detail = "identical" if match else "different"
        color = Fore.GREEN if match else Fore.RED
        print(f"{color}[{args.algo.upper()}] {status}: Hashes are {detail}.")
        print(f"Computed: {computed}")
        print(f"Provided: {args.compare.strip()}")
        sys.exit(0 if match else 1)
    else:
        print(computed)

if __name__ == "__main__":
    main()