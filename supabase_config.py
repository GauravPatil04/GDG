from supabase import create_client, Client

SUPABASE_URL = 'https://evqpuqeucgsqafflseug.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV2cXB1cWV1Y2dzcWFmZmxzZXVnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NDgyNzM2MywiZXhwIjoyMDYwNDAzMzYzfQ.vBDY4VXNOgNFFk9MMYgf9aAGgSAtgFMMY_fzPI49QQg'

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
