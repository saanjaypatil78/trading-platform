
import { createClient } from '@supabase/supabase-js';

// User provided Supabase URL
const supabaseUrl = 'https://rdsabmcqzujybjyzyqgg.supabase.co';
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';

if (!supabaseKey) {
    console.warn("Missing NEXT_PUBLIC_SUPABASE_ANON_KEY env variable");
}

export const supabase = createClient(supabaseUrl, supabaseKey);
