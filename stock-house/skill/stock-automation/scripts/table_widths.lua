local function cell_len(c)
  local s = pandoc.utils.stringify(c.contents)
  return utf8.len(s) or #s
end
function Table(t)
  local n = #t.colspecs
  local mx = {}
  for i=1,n do mx[i]=2 end
  local function scan(rows)
    for _,r in ipairs(rows) do
      for i,c in ipairs(r.cells) do
        if i<=n then local l=cell_len(c); if l>mx[i] then mx[i]=l end end
      end
    end
  end
  scan(t.head.rows)
  for _,b in ipairs(t.bodies) do scan(b.body) end
  local w, tot = {}, 0
  for i=1,n do w[i]=math.sqrt(math.min(mx[i],60))+0.8; tot=tot+w[i] end
  for i=1,n do t.colspecs[i] = {t.colspecs[i][1], w[i]/tot} end
  return t
end
