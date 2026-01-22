-- Enable RLS on the table
ALTER TABLE public.t_crawled_shops ENABLE ROW LEVEL SECURITY;

-- Create a policy that allows all operations (Select, Insert, Update, Delete)
-- Modify this if you need stricter access control (e.g., authenticated users only)
CREATE POLICY "Enable all access for crawler"
ON public.t_crawled_shops
FOR ALL
USING (true)
WITH CHECK (true);
