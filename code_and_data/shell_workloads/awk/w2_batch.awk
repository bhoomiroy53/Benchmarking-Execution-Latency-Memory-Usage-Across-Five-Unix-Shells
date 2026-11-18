# w2_batch.awk - batched aggregation of one subtree listing (Variant C).
# Input: lines from  find DIR -printf '%y %d %s %p\n'  (DIR is a top-level subdir).
# Writes 10 counters to -v out=PATH: files dirs empty depth csv dat json log txt csvlines
BEGIN { printf "" > out }
{
  t = $1; dep = $2 + 1; sz = $3; p = $4
  if (t == "d") { d++ }
  else if (t == "f") {
    f++
    if (sz == 0) e++
    if (dep > mx) mx = dep
    k = split(p, parts, "."); ext = parts[k]
    if (ext == "csv") { c++; while ((getline line < p) > 0) cl++; close(p) }
    else if (ext == "dat") da++
    else if (ext == "json") j++
    else if (ext == "log") l++
    else if (ext == "txt") tx++
  }
}
END { printf "%d %d %d %d %d %d %d %d %d %d\n", f, d, e, mx, c, da, j, l, tx, cl > out }
