// No console window on other platforms; irrelevant on Linux but harmless.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    blueboat_hub_lib::run();
}
