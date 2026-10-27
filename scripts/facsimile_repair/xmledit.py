"""Line-preserving edits of single-line start tags in XML text (no re-serialisation)."""
import re


def tag_span(text, local, attr, value, start=0):
    """Span (start, end) of the unique single-line start tag <local ... attr="value" ...> (prefix-agnostic)."""
    pat = re.compile(r'<(?:\w+:)?%s\b[^<>]*\s%s=(["\'])%s\1[^<>]*>' % (re.escape(local), re.escape(attr), re.escape(value)))
    hits = list(pat.finditer(text, start))
    if len(hits) != 1:
        raise ValueError(f'expected one <{local} {attr}="{value}">, found {len(hits)}')
    return hits[0].span()


def tag_at_line(text, local, line, must_contain=None):
    """Span of the only <local ...> start tag on the given 1-based line."""
    starts = [0] + [m.end() for m in re.finditer('\n', text)]
    a = starts[line - 1]
    b = starts[line] if line < len(starts) else len(text)
    pat = re.compile(r'<(?:\w+:)?%s\b[^<>]*>' % re.escape(local))
    hits = [m for m in pat.finditer(text, a, b) if must_contain is None or must_contain in m.group(0)]
    if len(hits) != 1:
        raise ValueError(f'line {line}: expected one <{local}> tag, found {len(hits)}: {text[a:b]!r}')
    return hits[0].span()


def set_attr(tag, attr, value):
    """Replace the value of attr in a start tag, keeping quotes and position. Raises if absent."""
    pat = re.compile(r'(\s%s=)(["\'])(.*?)\2' % re.escape(attr))
    m = pat.search(tag)
    if not m:
        raise ValueError(f'no @{attr} in {tag!r}')
    q = m.group(2)
    return tag[:m.start()] + m.group(1) + q + value + q + tag[m.end():]


def get_attr(tag, attr):
    m = re.search(r'\s%s=(["\'])(.*?)\1' % re.escape(attr), tag)
    return m.group(2) if m else None


def add_attr(tag, attr, value, after=None):
    """Add attr="value" after attribute `after` (or before the tag end)."""
    if get_attr(tag, attr) is not None:
        raise ValueError(f'@{attr} already present in {tag!r}')
    if after:
        m = re.search(r'\s%s=(["\']).*?\1' % re.escape(after), tag)
        if not m:
            raise ValueError(f'no @{after} in {tag!r}')
        return tag[:m.end()] + f' {attr}="{value}"' + tag[m.end():]
    end = tag.rstrip('>').rstrip('/').rstrip()
    rest = tag[len(end):]
    return end + f' {attr}="{value}"' + rest


def replace_span(text, span, new):
    return text[:span[0]] + new + text[span[1]:]
