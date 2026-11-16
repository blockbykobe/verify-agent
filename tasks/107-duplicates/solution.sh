cd /etc/app/nodes
find /etc/app/nodes -type f -print0 | xargs -0 sha256sum > /tmp/.sums
cut -c1-64 /tmp/.sums | sort | uniq -d > /tmp/.dups
grep -F -f /tmp/.dups /tmp/.sums | cut -c67- | LC_ALL=C sort > /tmp/duplicates.txt
rm -f /tmp/.sums /tmp/.dups
