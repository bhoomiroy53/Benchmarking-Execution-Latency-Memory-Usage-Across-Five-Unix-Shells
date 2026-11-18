# w1_batch.awk - batched single-pass aggregation of one log partition (Variant C).
# Writes 16 space-separated counters to the file/FIFO named by -v out=PATH.
# The BEGIN block opens the output first so a reader never blocks forever.
BEGIN { printf "" > out }
{
  n++
  c = substr($9, 1, 1)
  if (c == "2") s2++; else if (c == "3") s3++; else if (c == "4") s4++; else if (c == "5") s5++
  m = $6; gsub(/"/, "", m)
  if (m == "GET") g++; else if (m == "POST") po++; else if (m == "PUT") pu++; else if (m == "DELETE") de++
  b += $10
  if ($11 + 0 > mx) mx = $11 + 0
  split($7, p, "/"); r = p[4]
  if (r == "auth") ra++; else if (r == "items") ri++; else if (r == "orders") ro++; else if (r == "search") rs++; else if (r == "users") ru++
}
END { printf "%d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d\n", n, s2, s3, s4, s5, g, po, pu, de, b, mx, ra, ri, ro, rs, ru > out }
