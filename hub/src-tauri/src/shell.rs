//! Text helpers shared by several modules: POSIX shell quoting, a small
//! filename wildcard matcher and an ANSI-escape stripper.

/// Quote `s` for a POSIX shell. Plain words are returned unchanged.
pub fn sh_quote(s: &str) -> String {
    if !s.is_empty()
        && s
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || "-_./=:,+@%".contains(c))
    {
        return s.to_string();
    }
    format!("'{}'", s.replace('\'', "'\\''"))
}

/// Filename wildcard match: `*` (any run), `?` (one char); everything else literal.
pub fn wildcard_match(pattern: &str, name: &str) -> bool {
    let p: Vec<char> = pattern.chars().collect();
    let n: Vec<char> = name.chars().collect();
    let (mut pi, mut ni) = (0usize, 0usize);
    let (mut star, mut mark) = (None::<usize>, 0usize);
    while ni < n.len() {
        if pi < p.len() && (p[pi] == '?' || p[pi] == n[ni]) {
            pi += 1;
            ni += 1;
        } else if pi < p.len() && p[pi] == '*' {
            star = Some(pi);
            mark = ni;
            pi += 1;
        } else if let Some(s) = star {
            pi = s + 1;
            mark += 1;
            ni = mark;
        } else {
            return false;
        }
    }
    while pi < p.len() && p[pi] == '*' {
        pi += 1;
    }
    pi == p.len()
}

/// Remove ANSI escape sequences and control characters (keeps tabs) and
/// decode as lossy UTF-8. Used for last-line previews and the colcon parser.
pub fn strip_ansi(bytes: &[u8]) -> String {
    let mut out = Vec::with_capacity(bytes.len());
    let mut i = 0;
    while i < bytes.len() {
        let b = bytes[i];
        if b == 0x1b {
            i += 1;
            if i >= bytes.len() {
                break;
            }
            match bytes[i] {
                b'[' => {
                    // CSI: parameters/intermediates until a final byte 0x40..=0x7e
                    i += 1;
                    while i < bytes.len() && !(0x40..=0x7e).contains(&bytes[i]) {
                        i += 1;
                    }
                    i += 1;
                }
                b']' | b'P' | b'_' | b'^' => {
                    // OSC / DCS / APC / PM: until BEL or ESC \
                    i += 1;
                    while i < bytes.len() {
                        if bytes[i] == 0x07 {
                            i += 1;
                            break;
                        }
                        if bytes[i] == 0x1b && i + 1 < bytes.len() && bytes[i + 1] == b'\\' {
                            i += 2;
                            break;
                        }
                        i += 1;
                    }
                }
                b'(' | b')' | b'*' | b'+' => i += 2,
                _ => i += 1,
            }
            continue;
        }
        if b == b'\t' || b >= 0x20 && b != 0x7f {
            out.push(b);
        }
        i += 1;
    }
    String::from_utf8_lossy(&out).into_owned()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn quoting() {
        assert_eq!(sh_quote("abc"), "abc");
        assert_eq!(sh_quote("/home/u/worlds/p/w_1"), "/home/u/worlds/p/w_1");
        assert_eq!(sh_quote(""), "''");
        assert_eq!(sh_quote("a b"), "'a b'");
        assert_eq!(sh_quote("it's"), "'it'\\''s'");
        assert_eq!(sh_quote("$(rm -rf ~)"), "'$(rm -rf ~)'");
        assert_eq!(sh_quote("x;y"), "'x;y'");
    }

    #[test]
    fn wildcards() {
        assert!(wildcard_match("*-poslog.csv", "2026_11_11-12_06_36-sim-poslog.csv"));
        assert!(!wildcard_match("*-poslog.csv", "2026_11_11-12_06_36-sim-origin.yaml"));
        assert!(wildcard_match("*", ""));
        assert!(wildcard_match("a?c", "abc"));
        assert!(!wildcard_match("a?c", "ac"));
        assert!(wildcard_match("*.svlog", "x.svlog"));
        assert!(wildcard_match("world.sdf", "world.sdf"));
        assert!(!wildcard_match("world.sdf", "world.sdf.bak"));
        assert!(wildcard_match("*a*b*", "xxaxxbxx"));
    }

    #[test]
    fn ansi() {
        assert_eq!(strip_ansi(b"\x1b[1;32mFinished\x1b[0m <<< x"), "Finished <<< x");
        assert_eq!(strip_ansi(b"\x1b]0;title\x07hello"), "hello");
        assert_eq!(strip_ansi(b"a\x1b[Kb\x08c"), "abc");
        assert_eq!(strip_ansi("é\tz".as_bytes()), "é\tz");
    }
}
