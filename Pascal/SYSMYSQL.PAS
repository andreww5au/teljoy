unit sysMySQL;
{&Delphi+}
interface
uses Use32, libMySQL;

type
  PErrors               =^PChar;

var
  errmsg                : Array[0..16] of PErrors;

procedure my_init;

procedure init_alloc_root(var mem_root:MEM_ROOT;block_size:Word);
function  alloc_root(var mem_root:MEM_ROOT;Size:Word):Pointer;
procedure free_root(var root:MEM_ROOT);
function  strdup_root(var root:MEM_ROOT;const str:PChar):PChar;
function  memdup_root(var root:MEM_ROOT;const str:PChar;len:Word):PChar;
function my_multi_malloc(args:array of const):Pointer;

function atoi(st:String):Integer;
function int2str(int:Integer;buff:PChar;base:Integer):PChar;
function str2int(str:PChar;base,min,max:Integer;var int:Integer):PChar;
function StrMake(dest,src:PChar;len:Word):PChar;

implementation
uses SysUtils,NetLib;

const
  MALLOC_OVERHEAD       = 8;

function ALIGN_SIZE(size:Word):Word; inline; begin Result := (size+15) and not 15 end;

procedure init_alloc_root(var mem_root:MEM_ROOT;block_size:Word);
begin
  mem_root.free := nil;
  mem_root.used := nil;
  mem_root.min_malloc := 16;
  mem_root.block_size := block_size - MALLOC_OVERHEAD-sizeof(USED_MEM)-8;
  mem_root.error_handler := nil;
end;

function  alloc_root(var mem_root:MEM_ROOT;Size:Word):Pointer;
var
  get_size, max_left    : Word;
  point                 : PBYTE;
  next                  : PUSED_MEM;
  prev                  :^PUSED_MEM;
begin
  Size := ALIGN_SIZE(Size);
  prev := @mem_root.free;
  max_left := 0;
  next := prev^;
  while (next<>nil)and(next^.left < Size) do begin
    if next^.left > max_left then max_left := next^.left;
    prev := @next^.next;
    next := next^.next;
  end;
  if next=nil then begin        (* Time to alloc new block *)
    get_size := Size + ALIGN_SIZE(sizeof(USED_MEM));
    if (max_left*4 < mem_root.block_size)and(get_size<mem_root.block_size) then
      get_size := mem_root.block_size; (* Normal alloc *)

    next := AllocMem(get_size);
    if next=nil then begin
      if Assigned(mem_root.error_handler) then mem_root.error_handler;
      Result := nil;
      exit;
    end;
    next^.next := prev^;
    next^.size := get_size;
    next^.left := get_size-ALIGN_SIZE(sizeof(USED_MEM));
    prev^ := next;
  end;
  point := Pointer(next); inc(point,next^.size-next^.left);
  dec(next^.left,Size);
  if next^.left < mem_root.min_malloc then begin (* Full block *)
    prev^ := next^.next; (* Remove block from list *)
    next^.next := mem_root.used;
    mem_root.used := next;
  end;
  Result := point;
end;

procedure free_root(var root:MEM_ROOT);
var
  next, old             : PUSED_MEM;
begin
  if @root=nil then exit;
  next := root.used;
  while next<>nil do begin
    old := next; next := next^.next;
    FreeMem(old,old^.size);
  end;
  root.used := nil;
  next := root.free;
  while next<>nil do begin
    old := next; next := next^.next;
    FreeMem(old,old^.size);
  end;
  root.free := nil;
end;

function  strdup_root(var root:MEM_ROOT;const str:PChar):PChar;
var
  len                   : Word;
  pos                   : PChar;
begin
  len := StrLen(str) + 1;
  pos := alloc_root(root,len);
  if pos<>nil then StrMove(pos,str,len);
  Result := pos;
end;

function  memdup_root(var root:MEM_ROOT;const str:PChar;len:Word):PChar;
var
  pos                   : PChar;
begin
  pos := alloc_root(root,len);
  if pos<>nil then StrMove(pos,str,len);
  Result := pos;
end;

function atoi(st:String):Integer;
var
  v,e                   : Integer;
begin
  val(st,v,e);
  if e=0 then Result := v else Result := 0;
end;

function my_multi_malloc(args:array of const):Pointer;
var
  start,res             : PChar;
  pptr                  :^Pointer;
  tot_length,len        : Word;
  idx,max               : Integer;
begin
  tot_length := 0; idx := 0; Result := nil;
  max := ((High(args)+1)and not 1);
  while idx<max do begin
    if args[idx].vtype<>vtPointer then exit;
    pptr   := args[idx].vPointer;
    with args[idx+1] do case vtype of
      vtInteger : len := vInteger;
      vtString  : if vString = nil then len := 1 else len := Length(vString^)+1;
      vtPChar   : if vPChar = nil then len := 1 else len := StrLen(vPChar)+1;
      else exit;
    end;
    len := (len + 3) and not 3;
    inc(idx,2); inc(tot_length,len);
  end;
  start := AllocMem(tot_length);
  if start = nil then exit;

  res := start; idx := 0;
  while idx<max do begin
    pptr   := args[idx].vPointer;
    with args[idx+1] do case vtype of
      vtInteger : len := vInteger;
      vtString  : if vString = nil then len := 1 else len := Length(vString^)+1;
      vtPChar   : if vPChar = nil then len := 1 else len := StrLen(vPChar)+1;
      else exit;
    end;
    len := (len + 3) and not 3;
    pptr^  := res;
    inc(idx,2); inc(res,len);
  end;

  Result := start;
end;

function StrMake(dest,src:PChar;len:Word):PChar;
begin
  while len>0 do begin
    dec(len);
    dest^ := src^;
    inc(src);
    if dest^ = #0 then begin
      result := dest;
      exit;
    end;
    inc(dest);
  end;
  dest^ := #0;
  Result := dest;
end;

function str2int(str:PChar;base,min,max:Integer;var int:Integer):PChar;
var
  neg                   : Boolean;
begin
  int := 0; neg := False;
  while str^='-' do begin
    inc(str);
    neg := not neg;
  end;
  while (str^>='0')and(((base<11)and(str^<Chr(Ord('0')+base)))or
          ((base>10)and((str^<='9')or((UpCase(str^)>='A')and(UpCase(str^)<Chr(Ord('A')+base-10)))))) do begin
    int := int * base;
    if str^<='9' then
      inc(int,Ord(str^)-Ord('0'))
    else
      inc(int,Ord(UpCase(str^))-Ord('A')+10);
    inc(str);
  end;
  if neg then int := -int;
  if int<min then int := min else
  if int>max then int := max;
  if str^=#0 then
    Result := nil
  else
    Result := str;
end;

function int2str(int:Integer;buff:PChar;base:Integer):PChar;
var
  temp          : Array[0..32] of Char;
  tlen,rem      : Integer;
  neg           : Boolean;
begin
  tlen := 0;
  neg := int<0; if neg then int := -int;
  repeat
    rem := int;
    int := int div base;
    dec(rem,int*base);
    if rem<10 then
      temp[tlen] := Chr(Ord('0')+rem)
    else
      temp[tlen] := Chr(Ord('A')+rem-10);
    inc(tlen);
  until int <= 0;
  if neg then begin
    buff^ := '-';
    inc(buff);
  end;
  while tlen>0 do begin
    dec(tlen);
    buff^ := temp[tlen];
    inc(buff);
  end;
  buff^ := #0;
  Result := buff;
end;

procedure my_init;
begin
  sock_init;
end;


end.

