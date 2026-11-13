# elf-abi-diff

Review exported ELF symbol compatibility in CI. Feed the tool the text output of `readelf -Ws` from two builds; it reports removed, added and changed exported symbols without treating link-address movement as an ABI break.

```bash
python -m pip install "elf-abi-diff @ git+https://github.com/mysteryljn/elf-abi-diff.git"
readelf -Ws old.elf > old.readelf
readelf -Ws new.elf > new.readelf
elf-abi-diff compare old.readelf new.readelf --format html --output abi.html
```

The first release intentionally consumes `readelf -Ws` text so it works with any target architecture and does not execute or disassemble an ELF. It gates removed or changed global/weak defined symbols; DWARF types, C++ mangling policy, symbol version scripts and platform-specific ABI rules are outside the MVP. Use `--fail-on any-change` when additions also require review.

## Development

`python -m unittest discover -s tests -v` runs the offline suite. `demo` creates a report from the bundled synthetic readelf fixture. The fixture is synthetic and contains no production binary data.

MIT License.
