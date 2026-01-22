try:
    import supabase
    print("Supabase imported successfully")
    print(f"Supabase file: {supabase.__file__}")
except ImportError as e:
    print(f"Import failed: {e}")
except Exception as e:
    print(f"Other error: {e}")
