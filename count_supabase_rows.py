import requests
import config

def count_rows():
    headers = {
        "apikey": config.SUPABASE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_KEY}",
        "Prefer": "count=exact"
    }
    
    try:
        # Get total count
        url = f"{config.SUPABASE_URL}/rest/v1/{config.SUPABASE_TABLE}?select=*"
        resp = requests.head(url, headers=headers)
        total = resp.headers.get("Content-Range").split("/")[1]
        print(f"Total rows in {config.SUPABASE_TABLE}: {total}")
        
        # Get rows with emails
        # email is not null and email != ''
        # Postgrest syntax: email=not.is.null&email=neq.
        email_url = f"{config.SUPABASE_URL}/rest/v1/{config.SUPABASE_TABLE}?email=not.is.null&email=neq."
        resp_email = requests.head(email_url, headers=headers)
        email_total = resp_email.headers.get("Content-Range").split("/")[1]
        print(f"Rows with email in {config.SUPABASE_TABLE}: {email_total}")
        
        # Get sample of newest data
        sample_url = f"{config.SUPABASE_URL}/rest/v1/{config.SUPABASE_TABLE}?select=name,email,address&limit=20&order=created_at.desc"
        # Wait, if there's no created_at, just get limit 20
        # Let's try it
        resp_sample = requests.get(sample_url, headers={"apikey": config.SUPABASE_KEY, "Authorization": f"Bearer {config.SUPABASE_KEY}"})
        if resp_sample.status_code == 200:
            print("\nSample Data (Newest or First 20):")
            for row in resp_sample.json():
                print(f"- {row.get('name')} | {row.get('email')} | {row.get('address')}")
        else:
            # Fallback if created_at doesn't exist
            sample_url = f"{config.SUPABASE_URL}/rest/v1/{config.SUPABASE_TABLE}?select=name,email,address&limit=20"
            resp_sample = requests.get(sample_url, headers={"apikey": config.SUPABASE_KEY, "Authorization": f"Bearer {config.SUPABASE_KEY}"})
            print("\nSample Data (First 20):")
            for row in resp_sample.json():
                print(f"- {row.get('name')} | {row.get('email')} | {row.get('address')}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    count_rows()

if __name__ == "__main__":
    count_rows()
