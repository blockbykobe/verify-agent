#!/bin/bash
set -euo pipefail
printf '#!/bin/bash\necho backup done\n' > /usr/local/bin/backup.sh; chmod 755 /usr/local/bin/backup.sh
