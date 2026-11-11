-- Yvan.IA — cette fonction est appelée uniquement par le trigger auth.users.
-- Elle ne doit pas être exposée comme RPC à anon ou authenticated.
revoke all on function public.yvan_create_profile() from public;
revoke all on function public.yvan_create_profile() from anon;
revoke all on function public.yvan_create_profile() from authenticated;
