//! Exposes the pinned anytomd-rs version, read from the workspace lockfile, as ANYTOMD_ENGINE_VERSION.

use std::fs;

fn main() {
    let lock = "../../Cargo.lock";
    println!("cargo:rerun-if-changed={lock}");
    let text = fs::read_to_string(lock).expect("workspace Cargo.lock");
    let version = text
        .split("[[package]]")
        .find(|block| block.contains("name = \"anytomd\"\n"))
        .and_then(|block| {
            block
                .lines()
                .find_map(|line| line.strip_prefix("version = \""))
        })
        .and_then(|rest| rest.strip_suffix('"'))
        .expect("anytomd in Cargo.lock");
    println!("cargo:rustc-env=ANYTOMD_ENGINE_VERSION={version}");
}
