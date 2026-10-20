from collections import Counter


def _walk_parts(node):
    """Yield part_info for every part occurrence (shared nodes count each use)."""
    if node.__dict__.get("part_info") is not None:
        yield node.__dict__["part_info"]
    for child in getattr(node, "_children", ()):
        yield from _walk_parts(child)


class VEXAssembly:
    """Base class for assemblies; subclasses set self.shape."""

    shape = None

    def render(self, path):
        self.shape.save_as_scad(path)

    def bom(self):
        """Return [(PartInfo, quantity)] sorted by part name."""
        counts = Counter(_walk_parts(self.shape))
        return sorted(counts.items(), key=lambda kv: kv[0].name)

    def bom_total(self):
        """Total price of priced parts; unpriced parts are ignored."""
        return sum(p.price * q for p, q in self.bom() if p.price is not None)

    def bom_csv(self):
        rows = ["sku,name,quantity,unit_price,line_total"]
        for p, q in self.bom():
            unit = "" if p.price is None else f"{p.price:.2f}"
            total = "" if p.price is None else f"{p.price * q:.2f}"
            rows.append(f"{p.sku},{p.name},{q},{unit},{total}")
        return "\n".join(rows)
