Unit libMySQL;
{&Delphi+}
(* Copyright Abandoned 1996 TCX DataKonsult AB & Monty Program KB & Detron HB
   This file is public domain and comes with NO WARRANTY of any kind *)
(* Translated into Pascal by Antony T Curtis (1998) *)
interface
uses Use32, netMySQL;

const
(* Version numbers for protocol & mysqld *)

  MYSQL_SERVER_VERSION  = '3.21.33';
  FRM_VER               = 6;
  MYSQL_VERSION_ID      = 32133;
  PROTOCOL_VERSION      = 10;
{$IFDEF OS2}
  SYSTEM_TYPE           = 'vpOS/2';
{$ELSE}
  SYSTEM_TYPE           = 'vpWin32';
{$ENDIF}
{$IFOPT G5+}
  MACHINE_TYPE          = 'i586';
{$ELSE} {$IFOPT G4+}
  MACHINE_TYPE          = 'i486';
{$ELSE}
  MACHINE_TYPE          = 'i386';
{$ENDIF}
{$ENDIF}


type
  gptr                  = PChar;
  my_bool               = Boolean;

  PUSED_MEM             =^USED_MEM;
  USED_MEM              = record                (* struct for once_alloc *)
    next                : PUSED_MEM;            (* Next block in use *)
    left                : Word;                 (* memory left in block  *)
    size                : Word;                 (* size of block *)
  end;
  PMEM_ROOT             =^MEM_ROOT;
  MEM_ROOT              = record
    free                : PUSED_MEM;
    used                : PUSED_MEM;
    min_malloc          : Word;
    block_size          : Word;
    error_handler       : procedure;
  end;

(*
** Common definition between mysql server & client
*)
const
  NAME_LEN              = 64;                   (* Field/table name length *)
  LOCAL_HOST            = 'localhost';

  MYSQL_DEFAULT_PORT    = 3306;                 (* Alloced by ISI for MySQL *)
  MYSQL_UNIX_ADDR       = '\socket\mysql.sock'; (* OS/2 style IPC sockets *)

type
  enum_server_command   = (COM_SLEEP,COM_QUIT,COM_INIT_DB,COM_QUERY,
                           COM_FIELD_LIST,COM_CREATE_DB,COM_DROP_DB,COM_REFRESH,
                           COM_SHUTDOWN,COM_STATISTICS,
                           COM_PROCESS_INFO,COM_CONNECT,COM_PROCESS_KILL,
                           COM_DEBUG);

const
  NOT_NULL_FLAG         = 1;                    (* Field can't be NULL *)
  PRI_KEY_FLAG          = 2;                    (* Field is part of a primary key *)
  UNIQUE_KEY_FLAG       = 4;                    (* Field is part of a unique key *)
  MULTIPLE_KEY_FLAG     = 8;                    (* Field is part of a key *)
  BLOB_FLAG             = 16;                   (* Field is a blob *)
  UNSIGNED_FLAG         = 32;                   (* Field is unsigned *)
  ZEROFILL_FLAG         = 64;                   (* Field is zerofill *)
  BINARY_FLAG           = 128;
(* The following are only sent to new clients *)
  ENUM_FLAG             = 256;                  (* field is an enum *)
  AUTO_INCREMENT_FLAG   = 512;                  (* field is a autoincrement field *)
  TIMESTAMP_FLAG        = 1024;                 (* Field is a timestamp *)
  PART_KEY_FLAG         = 16384;                (* Intern; Part of some key *)
  GROUP_FLAG            = 32768;                (* Intern group field *)

  REFRESH_GRANT         = 1;                    (* Refresh grant tables *)
  REFRESH_LOG           = 2;                    (* Start on new log file *)
  REFRESH_TABLES        = 4;                    (* close all tables *)
  REFRESH_HOSTS         = 8;                    (* Flush host cache *)
  REFRESH_FAST          = 32768;                (* Intern flag *)

  CLIENT_LONG_PASSWORD  = 1;                    (* new more secure passwords *)
  CLIENT_FOUND_ROWS     = 2;                    (* Found instead of affected rows *)
  CLIENT_LONG_FLAG      = 4;                    (* Get all column flags *)
  CLIENT_CONNECT_WITH_DB= 8;                    (* One can specify db on connect *)
  CLIENT_NO_SCHEMA      = 16;                   (* Don't allow database.table.column *)

const
  packet_error          = Word($FFFFFFFF);

type
  enum_field_types      = byte;

const
  FIELD_TYPE_DECIMAL    = 0;
  FIELD_TYPE_TINY       = 1;
  FIELD_TYPE_SHORT      = 2;
  FIELD_TYPE_LONG       = 3;
  FIELD_TYPE_FLOAT      = 4;
  FIELD_TYPE_DOUBLE     = 5;
  FIELD_TYPE_NULL       = 6;
  FIELD_TYPE_TIMESTAMP  = 7;
  FIELD_TYPE_LONGLONG   = 8;
  FIELD_TYPE_INT24      = 9;
  FIELD_TYPE_DATE       = 10;
  FIELD_TYPE_TIME       = 11;
  FIELD_TYPE_DATETIME   = 12;
  FIELD_TYPE_YEAR       = 13;
  FIELD_TYPE_NEWDATE    = 14;
  FIELD_TYPE_ENUM       = 247;
  FIELD_TYPE_SET        = 248;
  FIELD_TYPE_TINY_BLOB  = 249;
  FIELD_TYPE_MEDIUM_BLOB= 250;
  FIELD_TYPE_LONG_BLOB  = 251;
  FIELD_TYPE_BLOB       = 252;
  FIELD_TYPE_VAR_STRING = 253;
  FIELD_TYPE_STRING     = 254;

  FIELD_TYPE_CHAR       = FIELD_TYPE_TINY;      (* For compability *)
  FIELD_TYPE_INTERVAL   = FIELD_TYPE_ENUM;      (* For compability *)

type
  rand_struct           = record
    seed,seed2,max_value: Cardinal;
    max_value_dbl       : Double;
  end;

  (* The following is for user defined functions *)

  PItem_result          =^Item_result;
  Item_result           = (STRING_RESULT,REAL_RESULT,INT_RESULT);

  UDF_ARGS              = record
    arg_count           : Word;                 (* Number of arguments *)
    arg_type            : PItem_result;         (* Pointer to item_results *)
    args                :^PChar;                (* Pointer to argument *)
    lengths             :^Cardinal;             (* Length of string arguments *)
  end;

  (* This holds information about the result *)

  UDF_INIT              = record
    maybe_null          : my_bool;              (* 1 if function can return NULL *)
    decimals            : Word;                 (* for real functions *)
    max_length          : Word;                 (* For string functions *)
    ptr                 : PChar;                (* free pointer for function data *)
  end;

  (* Prototypes to password functions *)

procedure randominit(var rand:rand_struct;seed1,seed2:Cardinal);
procedure make_scrambled_password(pto:PChar;const password:PChar);
procedure get_salt_from_password(var result;const password:PChar);
function  scramble(pto:PChar;const msg,passwd:PChar;old_ver:my_bool):PChar;
function  check_scramble(const scramble,msg:PChar;var salt;old_ver:my_bool):my_bool;
//function  get_tty_password(opt_message:PChar):PChar;

const
  NULL_LENGTH           = Cardinal($FFFFFFFF);  (* For net_store_length *)


const
  mysql_port            : Word  = 0;
  mysql_unix_port       : PChar = nil;

function IS_PRI_KEY(n:Word):Boolean; inline; begin Result := (n and PRI_KEY_FLAG)<>0 end;
function IS_NOT_NULL(n:Word):Boolean; inline; begin Result := (n and NOT_NULL_FLAG)<>0 end;
function IS_BLOB(n:Word):Boolean; inline; begin Result := (n and BLOB_FLAG)<>0 end;
function IS_NUM(t:enum_field_types):Boolean; inline; begin Result := (t <= FIELD_TYPE_INT24) or (t = FIELD_TYPE_YEAR) end;

type
  PMYSQL_FIELD          =^MYSQL_FIELD;
  MYSQL_FIELD           = record
    fname               : PChar;                (* Name of column *)
    table               : PChar;                (* Table of column if column was a field *)
    def                 : PChar;                (* Default value (set by mysql_list_fields) *)
    ftype               : enum_field_types;     (* Type of field. Se mysql_com.h for types *)
    length              : Word;                 (* Width of column *)
    max_length          : Word;                 (* Max width of selected set *)
    flags               : Word;                 (* Div flags *)
    decimals            : Word;                 (* Number of decimals in field *)
  end;

  PMYSQL_ROW            =^MYSQL_ROW;
  MYSQL_ROW             = Array[0..High(Integer)div 4] of PChar; (* return data as array of strings *)

  MYSQL_FIELD_OFFSET    = Word;                 (* offset to current field *)

  PMYSQL_ROWS           =^MYSQL_ROWS;
  MYSQL_ROWS            = record
    next                : PMYSQL_ROWS;          (* list of rows *)
    data                : PMYSQL_ROW;
  end;

  MYSQL_ROW_OFFSET      =^MYSQL_ROWS;           (* offset to current row *)

  PMYSQL_DATA           =^MYSQL_DATA;
  MYSQL_DATA            = record
    rows                : Word;
    fields              : Word;
    data                : PMYSQL_ROWS;
    alloc               : MEM_ROOT;
  end;

  mysql_status          = (MYSQL_STATUS_READY,MYSQL_STATUS_GET_RESULT,
                           MYSQL_STATUS_USE_RESULT);

  PMYSQL                =^MYSQL;
  MYSQL                 = record
    net                 : NET;                  (* Communication parameters *)
    host,user,passwd    : PChar;
    unix_socket         : PChar;
    server_version      : PChar;
    host_info,info,db   : PChar;
    port, client_flag   : Word;
    server_capabilities : Word;
    protocol_version    : Word;
    field_count         : Word;
    thread_id           : Word;                 (* Id for connection in server *)
    affected_rows       : Cardinal;
    insert_id           : Cardinal;             (* id if insert on table with NEXTNR *)
    extra_info          : Cardinal;             (* Used by mysqlshow *)
    status              : mysql_status;
    fields              : PMYSQL_FIELD;
    field_alloc         : MEM_ROOT;
    free_me             : my_bool;              (* If free in mysql_close *)
    reconnect           : my_bool;              (* set to 1 if automatic reconnect *)
  end;

  PMYSQL_RES            =^MYSQL_RES;
  MYSQL_RES             = record
    row_count           : Cardinal;
    field_count         : Word;
    current_field       : Word;
    fields              : PMYSQL_FIELD;
    data                : PMYSQL_DATA;
    data_cursor         : PMYSQL_ROWS;
    field_alloc         : MEM_ROOT;
    row                 : PMYSQL_ROW;           (* If unbuffered read *)
    current_row         : PMYSQL_ROW;           (* buffer to current row *)
    lengths             : PWord;                (* column lengths of current row *)
    handle              : PMYSQL;               (* for unbuffered reads *)
    eof                 : my_bool;              (* Used my mysql_fetch_row *)
  end;

function  mysql_connect(mysql:PMYSQL;const host,user,passwd:PChar):PMYSQL;
function  mysql_real_connect(mysql:PMYSQL;const host,user,passwd:PChar;
          port:Word; const unix_socket:PChar; client_flag:Word):PMYSQL;
procedure mysql_close(mysql:PMYSQL);
function  mysql_select_db(mysql:PMYSQL;const db:PChar):Integer;
function  mysql_query(mysql:PMYSQL;const query:PChar):Integer;
function  mysql_real_query(mysql:PMYSQL;const query:PChar;len:Word):Integer;
function  mysql_create_db(mysql:PMYSQL;const DB:PChar):Integer;
function  mysql_drop_db(mysql:PMYSQL;const DB:PChar):Integer;
function  mysql_shutdown(mysql:PMYSQL):Integer;
function  mysql_dump_debug_info(mysql:PMYSQL):Integer;
function  mysql_refresh(mysql:PMYSQL;options:Word):Integer;
function  mysql_kill(mysql:PMYSQL;pid:Cardinal):Integer;
function  mysql_stat(mysql:PMYSQL):PChar;
function  mysql_get_server_info(mysql:PMYSQL):PChar;
function  mysql_get_client_info:PChar;
function  mysql_get_host_info(mysql:PMYSQL):PChar;
function  mysql_get_proto_info(mysql:PMYSQL):Word;
function  mysql_list_dbs(mysql:PMYSQL;const wild:PChar):PMYSQL_RES;
function  mysql_list_tables(mysql:PMYSQL;const wild:PChar):PMYSQL_RES;
function  mysql_list_fields(mysql:PMYSQL;const table,wild:PChar):PMYSQL_RES;
function  mysql_list_processes(mysql:PMYSQL):PMYSQL_RES;
function  mysql_store_result(mysql:PMYSQL):PMYSQL_RES;
function  mysql_use_result(mysql:PMYSQL):PMYSQL_RES;
procedure mysql_free_result(result:PMYSQL_RES);
procedure mysql_data_seek(res:PMYSQL_RES;row:Word);
function  mysql_row_seek(res:PMYSQL_RES;row:MYSQL_ROW_OFFSET):MYSQL_ROW_OFFSET;
function  mysql_field_seek(res:PMYSQL_RES;fieldnr:MYSQL_FIELD_OFFSET):MYSQL_FIELD_OFFSET;
function  mysql_fetch_row(res:PMYSQL_RES):PMYSQL_ROW;
function  mysql_fetch_lengths(res:PMYSQL_RES):PWord;
function  mysql_fetch_field(res:PMYSQL_RES):PMYSQL_FIELD;
function  mysql_escape_string(sto:PChar;const from:PChar;from_length:Word):Word;
function  mysql_unescape_string(sto:PChar;const from:PChar):Word;
procedure mysql_debug(debug:PChar);

function mysql_num_rows(res:PMYSQL_RES):Cardinal; inline; begin Result := res^.row_count end;
function mysql_num_fields(res:PMYSQL_RES):Word; inline; begin Result := res^.field_count end;
function mysql_eof(res:PMYSQL_RES):Boolean; inline; begin Result := res^.eof end;
function mysql_fetch_field_direct(res:PMYSQL_RES;fieldnr:Integer):PMYSQL_FIELD; inline;
         begin Result := res^.fields; inc(Result,fieldnr) end;
function mysql_fetch_fields(res:PMYSQL_RES):PMYSQL_FIELD; inline; begin Result := res^.fields end;
function mysql_row_tell(res:PMYSQL_RES):PMYSQL_ROWS; inline; begin Result := res^.data_cursor end;
function mysql_field_tell(res:PMYSQL_RES):Word; inline; begin Result := res^.current_field end;

function mysql_affected_rows(mysql:PMYSQL):Cardinal; inline; begin Result := mysql^.affected_rows end;
function mysql_insert_id(mysql:PMYSQL):Cardinal; inline; begin Result := mysql^.insert_id end;
function mysql_error(mysql:PMYSQL):PChar; inline; begin Result := mysql^.net.last_error end;
function mysql_errno(mysql:PMYSQL):Word; inline; begin Result := mysql^.net.last_errno end;
function mysql_info(mysql:PMYSQL):PChar; inline; begin Result := mysql^.info end;
function mysql_reload(mysql:PMYSQL):Integer; inline; begin Result := mysql_refresh(mysql,REFRESH_GRANT) end;
function mysql_thread_id(mysql:PMYSQL):Word; inline; begin Result := mysql^.thread_id end;


(* new api functions *)
const
  HAVE_MYSQL_REAL_CONNECT       = 1;

(* Copyright Abandoned 1996 TCX DataKonsult AB & Monty Program KB & Detron HB
   This file is public domain and comes with NO WARRANTY of any kind *)

(* Error messages for mysql clients *)
(* error messages for the demon is in share/language/errmsg.sys *)

procedure init_client_errs;
const
  client_errors                 : Array[0..14] of PChar = (           (* Error messages *)
    'Unknown MySQL error',
    'Can''t create UNIX socket',
    'Can''t connect to local MySQL server',
    'Can''t connect to MySQL server on %s (%d)',
    'Can''t create IP socket',
    'Unknown MySQL Server Host (%s) (%d)',
    'MySQL server has gone away',
    'Protocol mismatch. Server Version = %d Client Version = %d',
    'MySQL client got out of memory',
    'Wrong host info',
    'Localhost via UNIX socket',
    '%s via TCP/IP',
    'Error in server handshake',
    'Lost connection to MySQL server during query',
    'Commands out of sync;  You can''t run this command now');

const
  CR_MIN_ERROR                  = 2000;   (* For easier client code *)
  CR_MAX_ERROR                  = 2999;

function ER(X:integer):PChar; inline; begin
  if (X-CR_MIN_ERROR<0)or(X-CR_MIN_ERROR>High(client_errors)) then Result := client_errors[0] else
  Result := client_errors[X - CR_MIN_ERROR];
  if Result = nil then Result := '';
end;

const
  CLIENT_ERRMAP                 = 2;       (* Errormap used by my_error() *)

  CR_UNKNOWN_ERROR              = 2000;
  CR_SOCKET_CREATE_ERROR        = 2001;
  CR_CONNECTION_ERROR           = 2002;
  CR_CONN_HOST_ERROR            = 2003;
  CR_IPSOCK_ERROR               = 2004;
  CR_UNKNOWN_HOST               = 2005;
  CR_SERVER_GONE_ERROR          = 2006;
  CR_VERSION_ERROR              = 2007;
  CR_OUT_OF_MEMORY              = 2008;
  CR_WRONG_HOST_INFO            = 2009;
  CR_LOCALHOST_CONNECTION       = 2010;
  CR_TCP_CONNECTION             = 2011;
  CR_SERVER_HANDSHAKE_ERR       = 2012;
  CR_SERVER_LOST                = 2013;
  CR_COMMANDS_OUT_OF_SYNC       = 2014;
  CR_NAMEDPIPE_CONNECTION       = 2015;
  CR_NAMEDPIPEWAIT_ERROR        = 2016;
  CR_NAMEDPIPEOPEN_ERROR        = 2017;
  CR_NAMEDPIPESETSTATE_ERROR    = 2018;


implementation
uses Dos, NetLib, SysUtils, sysMySQL, Math;

const
  mysql_client_init     : my_bool       = false;
var
  current_mysql         : PMYSQL;

const
  CLIENT_CAPABILITIES   = (CLIENT_LONG_PASSWORD or CLIENT_LONG_FLAG);

function  read_rows(var mysql:MYSQL;mysql_fields:PMYSQL_FIELD;fields:Word):PMYSQL_DATA; forward;
procedure end_server(var mysql:MYSQL); forward;
procedure remember_connection(var mysql:MYSQL); forward;
procedure read_user_name(name:PChar); forward;
procedure append_wild(pto,pend:PChar;const wild:PChar); forward;

type
  NET_st                = NET;
  MYSQL_st              = MYSQL;

function uint2korr(var p):Word;
var
  A                     : Array[0..1] of Byte absolute p;
begin
  Result := A[0] or (A[1] shl 8);
end;

function uint3korr(var p):Word;
var
  A                     : Array[0..2] of Byte absolute p;
begin
  Result := A[0] or ((A[1] or (A[2] shl 8)) shl 8);
end;

function uint4korr(var p):Word;
var
  A                     : Array[0..3] of Byte absolute p;
begin
  Result := A[0] or ((A[1] or ((A[2] or (A[3] shl 8)) shl 8)) shl 8);
end;

function uint5korr(var p):Comp;
var
  A                     : Array[0..4] of Byte absolute p;
begin
  Result := A[4];
  Result := (Result * 256) + A[3];
  Result := (Result * 256) + A[2];
  Result := (Result * 256) + A[1];
  Result := (Result * 256) + A[0];
end;

function uint8korr(var p):Comp;
var
  A                     : Array[0..7] of Byte absolute p;
begin
  Result := A[7];
  Result := (Result * 256) + A[6];
  Result := (Result * 256) + A[5];
  Result := (Result * 256) + A[4];
  Result := (Result * 256) + A[3];
  Result := (Result * 256) + A[2];
  Result := (Result * 256) + A[1];
  Result := (Result * 256) + A[0];
end;

procedure int2store(T:Pointer;A:Integer);
var
  Tp                    : PBYTE absolute T;
begin
  Tp^ := A and $FF; inc(Tp); A := A shr 8;
  Tp^ := A and $FF;
end;

procedure int3store(T:Pointer;A:Integer);
var
  Tp                    : PBYTE absolute T;
begin
  Tp^ := A and $FF; inc(Tp); A := A shr 8;
  Tp^ := A and $FF; inc(Tp); A := A shr 8;
  Tp^ := A and $FF;
end;

procedure int4store(T:Pointer;A:Integer);
var
  Tp                    : PBYTE absolute T;
begin
  Tp^ := A and $FF; inc(Tp); A := A shr 8;
  Tp^ := A and $FF; inc(Tp); A := A shr 8;
  Tp^ := A and $FF; inc(Tp); A := A shr 8;
  Tp^ := A and $FF;
end;

procedure int5store(T:Pointer;A:Comp);
var
  Tp                    : PBYTE absolute T;
  Aw                    : Word;
begin
  Tp^ := Aw and $FF; inc(Tp); A := A / 256;
  Tp^ := Aw and $FF; inc(Tp); A := A / 256;
  Tp^ := Aw and $FF; inc(Tp); A := A / 256;
  Tp^ := Aw and $FF; inc(Tp); A := A / 256;
  Tp^ := Aw and $FF;
end;

(*****************************************************************************
** read a packet from server. Give error message if socket was down
** or package is an error message
*****************************************************************************)

function do_my_net_read(var net:NET;var len:Word):Word;
begin len := my_net_read(net); Result := len end;

function net_safe_read(var mysql:MYSQL):Word;
var
  net                   : NET_st absolute mysql;
  len                   : Word;
  ppos                  : PBYTE;
begin
  len := 0;

  if (net.fd < 0) or (do_my_net_read(net,len) = packet_error) or (len = 0) then begin
    //DBUG_PRINT("error",("Wrong connection or packet. fd: %d  len: %d",
    //                    net->fd,len));
    //WriteLn(Format('Wrong connection or packet. fd: %d  len: %d',[net.fd,len]));
    end_server(mysql);
    net.last_errno := CR_SERVER_LOST;
    StrCopy(net.last_error,ER(net.last_errno));
    Result := packet_error;
    exit;
  end;
  if net.buff^ = 255 then begin
    if len > 3 then begin
      ppos := net.buff; inc(ppos);
      if mysql.protocol_version > 9 then begin
                                                (* New client protocol *)
        net.last_errno := uint2korr(ppos^);
        inc(ppos,2);
      end else
        net.last_errno := CR_UNKNOWN_ERROR;
      StrMove(net.last_error,PChar(ppos),sizeof(net.last_error)-1);
    end else begin
      net.last_errno := CR_UNKNOWN_ERROR;
      StrCopy(net.last_error,ER(net.last_errno));
    end;
    //DBUG_PRINT("error",("Got error: %d (%s)", net->last_errno,
    //                    net->last_error));
    Result := packet_error;
    exit;
  end;
  Result := len;
end;


(* Get the length of next field. Change parameter to point at fieldstart *)
function net_field_length(var packet:PBYTE):Word;
var
  ppos          : PBYTE;
begin
  ppos := packet;
  if ppos^ < 251 then begin
    inc(packet);
    Result := ppos^;
    exit;
  end;
  if ppos^ = 251 then begin
    inc(packet);
    Result := NULL_LENGTH;
    exit;
  end;
  if ppos^ = 252 then begin
    inc(packet,3);inc(ppos);
    result := uint2korr(ppos^);
    exit;
  end;
  if ppos^ = 253 then begin
    inc(packet,4);inc(ppos);
    result := uint3korr(ppos^);
  end;
  inc(packet,6); inc(ppos);     (* Must be 254 when here *)
  result := uint4korr(ppos^);
end;

procedure free_rows(cur:PMYSQL_DATA);
begin
  if cur<>nil then begin
    free_root(cur^.alloc);
    FreeMem(cur,SizeOf(cur^));
  end;
end;


function mysql_reconnect(mysql:PMYSQL):Boolean;
var
  tmp_mysql             : MYSQL_st;
begin

  if not (mysql^.reconnect) or (mysql^.host_info=nil) then begin
    Result := True;
    exit;
  end;

  if mysql_real_connect(@tmp_mysql,mysql^.host,mysql^.user,mysql^.passwd,
                          mysql^.port,mysql^.unix_socket,
                          mysql^.client_flag)=nil then begin
    Result := True;
    exit;
  end;

  if (mysql^.db<>nil) and (mysql_select_db(@tmp_mysql,mysql^.db)<>0) then begin
    mysql_close(Pointer(@tmp_mysql));
    Result := true;
    exit;
  end;
  tmp_mysql.free_me := mysql^.free_me;
  mysql^.free_me := false;
  mysql_close(mysql);
  move(tmp_mysql,mysql^,sizeof(tmp_mysql));
  net_clear(mysql^.net);
  mysql^.affected_rows := Cardinal(not 0);
  Result := false;
end;

function simple_command(var mysql:MYSQL;command:enum_server_command;const arg:PChar;length:Word;skipp_check:my_bool):Integer;
var
  net                   : NET_st absolute mysql;
  len                   : Word;
  my_arg                : PChar;
begin
  if mysql.net.fd < 0 then begin              (* Do reconnect if possible *)
    if mysql_reconnect(Pointer(@mysql)) then begin
      net.last_errno := CR_SERVER_GONE_ERROR;
      StrCopy(net.last_error,ER(net.last_errno));
      Result := -1;
      exit;
    end;
  end;
  if mysql.status <> MYSQL_STATUS_READY then begin
    net.last_errno := CR_COMMANDS_OUT_OF_SYNC;
    StrCopy(net.last_error,ER(net.last_errno));
    Result := -1;
    exit;
  end;

  net.last_error[0] := #0;
  net.last_errno := 0;
  mysql.info := nil;
  mysql.affected_rows := Cardinal(not 0);
  remember_connection(mysql);
  net_clear(net);                       (* Clear receive buffer *)
  if arg=nil then my_arg := '' else my_arg := arg;
  if length<>0 then len := length else len := StrLen(my_arg);
  if net_write_command(net,Ord(command),Pointer(my_arg),len)<>0 then begin
    //DBUG_PRINT("error",("Can't send command to server. Error: %d",errno));
    end_server(mysql);
    if mysql_reconnect(@mysql) or
       (net_write_command(net,Ord(command),Pointer(my_arg),len)<>0) then begin
      net.last_errno := CR_SERVER_GONE_ERROR;
      StrCopy(net.last_error,ER(net.last_errno));
      Result := -1;
      exit;
    end;
  end;
  if not skipp_check then begin
    if net_safe_read(mysql) = packet_error then
      Result := -1
    else
      Result := 0
  end else
    Result := 0;
end;

procedure free_old_query(var mysql:MYSQL);
begin
  //DBUG_ENTER("free_old_query");
  if mysql.fields <> nil then free_root(mysql.field_alloc);
  init_alloc_root(mysql.field_alloc,8192);    (* Assume rowlength < 8192 *)
  mysql.fields := nil;
  mysql.field_count := 0;                         (* For API *)
end;

const
  USERNAMELENGTH        = 16;

procedure read_user_name(name:PChar);
const
  str                   : String = '';
begin
  if str[0]=#0 then str := GetEnv('USER');
  if str[0]=#0 then str := GetEnv('LOGNAME');
  if str[0]=#0 then str := GetEnv('LOGIN');
  if str[0]=#0 then str := 'ODCB';
  str[1+Length(str)] := #0;
  StrMove(name,Pointer(@str[1]),USERNAMELENGTH);
end;

(*
** Expand wildcard to a sql string
*)

procedure append_wild(pto,pend:PChar;const wild:PChar);
var
  my_wild               : PChar;
begin
  dec(pend,5);                                       (* Some extra *)
  if (wild<>nil)and(wild^<>#0) then begin
    my_wild := wild;
    pto := StrECopy(pto,' like ''');
    while (my_wild^<>#0)and(Word(pto)<Word(pend)) do begin
      if (my_wild^ = '\')or(my_wild^ = '''') then begin
        pto^ := '\';
        inc(pto);
      end;
      pto^ := my_wild^;
      inc(pto); inc(my_wild);
    end;
    if my_wild^<>#0 then begin                  (* Too small buffer *)
      pto^ := '%';                              (* Nicer this way *)
      inc(pto);
    end;
    pto^ := ''''; inc(pto);
    pto^ := #0;
  end;
end;

(**************************************************************************
** Init debugging if MYSQL_DEBUG environment variable is found
**************************************************************************)

procedure mysql_debug(debug:PChar);
begin
end;


(**************************************************************************
** Store the server socket currently in use
** Used by pipe_handler if error on socket interrupt
**************************************************************************)

procedure remember_connection(var mysql:MYSQL);
begin
  current_mysql := Pointer(@mysql);
end;

(**************************************************************************
** Shut down connection
**************************************************************************)

procedure end_server(var mysql:MYSQL);
begin
  //DBUG_ENTER("end_server");
  if mysql.net.fd >= 0 then begin
    //DBUG_PRINT("enter",("Socket: %d", mysql->net.fd));
    shutdown(mysql.net.fd,2);
    soclose(mysql.net.fd);
    mysql.net.fd := -1;
    net_end(mysql.net);
    free_old_query(mysql);
  end;
  //DBUG_VOID_RETURN;
end;


procedure mysql_free_result(result:PMYSQL_RES);
begin
  //DBUG_ENTER("mysql_free_result");
  //DBUG_PRINT("enter",("mysql_res: %lx",result));
  if result<>nil then begin
    free_rows(result^.data);
    if result^.fields <> nil then
      free_root(result^.field_alloc);
    if result^.row <> nil then
      FreeMem(result^.row,result^.row_count * sizeof(MYSQL_ROWS));
    FreeMem(result,sizeof(MYSQL_RES));
  end;
  //DBUG_VOID_RETURN;
end;


(***************************************************************************
** Change field rows to field structs
***************************************************************************)

function unpack_fields(var data:MYSQL_DATA;var alloc:MEM_ROOT;fields:Word;
              default_value, long_flag_protocol:my_bool):PMYSQL_FIELD;
var
  row                   : PMYSQL_ROWS;
  field                 : PMYSQL_FIELD;
begin
  //DBUG_ENTER("unpack_fields");

  field := alloc_root(alloc,sizeof(MYSQL_FIELD)*fields);
  result := field;
  if result=nil then exit;

  row := data.data;
  while row<>nil do begin
    field^.table := strdup_root(alloc,row^.data^[0]);
    field^.fname := strdup_root(alloc,row^.data^[1]);
    field^.length:= uint3korr(row^.data^[2]^);
    field^.ftype := enum_field_types(row^.data^[3]^);
    if long_flag_protocol then begin
      field^.flags := uint2korr(row^.data^[4]^);
      field^.decimals := PByte(row^.data^[4]+2)^;
    end else begin
      field^.flags := PByte(row^.data^[4])^;
      field^.decimals := PByte(row^.data^[4]+1)^;
    end;
    if default_value and (row^.data^[5]<>nil) then
      field^.def := strdup_root(alloc,row^.data^[5])
    else
      field^.def := nil;
    field^.max_length := 0;
    row := row^.next; inc(field);
  end;
  free_rows(Pointer(@data));                              (* Free old data *)
end;


(* Read all rows (fields or data) from server *)

function read_rows(var mysql:MYSQL;mysql_fields:PMYSQL_FIELD;fields:Word):PMYSQL_DATA;
var
  net                   : NET_st absolute mysql;
  prev_ptr              :^PMYSQL_ROWS;
  cur                   : PMYSQL_ROWS;
  fld                   : PMYSQL_FIELD;
  pto, cp               : PChar;
  field, pkt_len        : Word;
  len                   : LongInt;
begin
  Result := nil;
  pkt_len := net_safe_read(mysql);
  if pkt_len = packet_error then exit;
  Result := AllocMem(sizeof(MYSQL_DATA));
  if Result = nil then begin
    net.last_errno := CR_OUT_OF_MEMORY;
    StrCopy(net.last_error,ER(net.last_errno));
    exit;
  end;
  init_alloc_root(result^.alloc,8192);         (* Assume rowlength < 8192 *)
  result^.alloc.min_malloc := sizeof(MYSQL_ROWS);
  prev_ptr := @result^.data;
  result^.rows := 0;
  result^.fields := fields;


  while (net.buff^ <> 254) or (pkt_len <> 1) do begin
    cp := Pointer(net.buff);
    inc(Result^.rows);
    cur := alloc_root(result^.alloc,sizeof(MYSQL_ROWS));
    if cur<>nil then
      cur^.data := alloc_root(result^.alloc,(fields+1)*sizeof(PChar)+pkt_len);
    if (cur=nil) or (cur^.data = nil) then begin
      free_rows(result);
      net.last_errno := CR_OUT_OF_MEMORY;
      StrCopy(net.last_error,ER(net.last_errno));
      Result := nil;
      exit;
    end;
    prev_ptr^ := cur;
    prev_ptr := @cur^.next;
    pto := Pointer(cur^.data); inc(pto,(fields+1)*SizeOf(PChar));
    for field := 0 to fields-1 do begin
      len := net_field_length(PBYTE(cp));
      if len = NULL_LENGTH then begin
        cur^.data^[field] := nil;                (* null field *)
      end else begin
        cur^.data^[field] := pto;
        Move(cp^,pto^,len);
        inc(pto,len); pto^ := #0; inc(pto);
        inc(cp,len);
        if mysql_fields <> nil then begin
          fld := mysql_fields; inc(fld,field);
          if fld^.max_length < len then
            fld^.max_length := len;
        end;
      end;
    end;
    cur^.data^[field] := pto;                        (* End of last field *)
    pkt_len := net_safe_read(mysql);
    if pkt_len = packet_error then begin
      free_rows(result);
      Result := nil;
      exit;
    end;
  end;
  prev_ptr^ := nil;                                 (* last pointer is null *)
end;


(*
** Read one row. Uses packet buffer as storage for fields.
** When next package is read, the previous field values are destroyed
*)


function read_one_row(var mysql:MYSQL;fields:Word;var row:MYSQL_ROW;lengths:PWord): Integer;
var
  field, pkt_len, len           : Word;
  pos, prev_pos                 : PChar;
begin
  pkt_len := net_safe_read(mysql);
  if pkt_len = packet_error then
    Result := -1
  else
  if (pkt_len = 1) and (mysql.net.buff^ = 254) then
    Result := 1                         (* End of data *)
  else begin
    prev_pos := nil;                    (* allowed to write at packet[-1] *)
    pos := Pointer(mysql.net.buff);
    for field := 0 to fields-1 do begin
      len := net_field_length(PBYTE(pos));
      if len = NULL_LENGTH then begin
        row[field] := nil;
        lengths^ := 0;
        inc(lengths);
      end else begin
        row[field] := pos;
        inc(pos,len);
        lengths^ := len;
        inc(lengths);
      end;
      if prev_pos<>nil then prev_pos^ := #0;    (* Terminate prev field *)
      prev_pos := pos;
    end;
    row[field] := prev_pos+1;                   (* End of last field *)
    prev_pos^ := #0;                            (* Terminate last field *)
    Result := 0;
  end;
end;


(**************************************************************************
** Connect to sql server
** If host == 0 then use localhost
**************************************************************************)

procedure mysql_init(mysql:PMYSQL);
begin
  FillChar(mysql^,sizeof(mysql^),0);
end;

function mysql_connect(mysql:PMYSQL;const host,user,passwd:PChar):PMYSQL;
begin
  Result := mysql_real_connect(mysql,host,user,passwd,0,{NullS}nil,0);
end;

function mysql_real_connect(mysql:PMYSQL;const host,user,passwd:PChar;
                          port:Word; const unix_socket:PChar; client_flag:Word):PMYSQL;
const
  sys_passwd            : String = '';
  sys_unixport          : String = '';
var
  buff                  : Array[0..99] of Char;
  scramble_buff         : Array[0..32] of Char;
  envstr,hoststr        : String;
  pend, host_info, env  : PChar;
  my_passwd, my_host    : PChar;
  my_unix_socket        : PChar;
  my_user               : PChar;
  sock, opt             : Integer;
  ip_addr               : LongInt;
  sock_addr             : sockaddr_in;
  unix_addr             : sockaddr_un;
  serv_ptr              : PSERVENT;
  hp                    : PHOSTENT;
  pkt_length            : Word;
  net                   :^NET_st;
label
  error;
begin
  Result := nil;

  if passwd=nil then begin
    sys_passwd := GetEnv('MYSQL_PWD');(* read Password from environment (haneke) *)
    sys_passwd[length(sys_passwd)+1] := #0;
    my_passwd := @sys_passwd[1];
  end else my_passwd := passwd;

  if not mysql_client_init then begin
    mysql_client_init := True;
    my_init;
    init_client_errs;
    if mysql_port = 0 then begin
      mysql_port := MYSQL_DEFAULT_PORT;

      serv_ptr := getservbyname('mysql','tcp');
      if serv_ptr <> nil then
        mysql_port := ntohs(serv_ptr^.s_port);
      envstr := GetEnv('MYSQL_TCP_PORT');
      if length(envstr)>0 then
        mysql_port := atoi(envstr);
    end;
    if mysql_unix_port = nil then begin
      mysql_unix_port := MYSQL_UNIX_ADDR;
      sys_unixport := GetEnv('MYSQL_UNIX_PORT');
      if length(sys_unixport)>0 then begin
        sys_unixport[length(sys_unixport)+1] := #0;
        mysql_unix_port := Pointer(@sys_unixport[1]);
      end;
    end;
    //mysql_debug(NullS);
  end;

  //DBUG_PRINT("enter",("host: %s",host ? host : "(Null)"));
  if mysql = nil then begin
    mysql := AllocMem(SizeOf(mysql^));
    if mysql=nil then exit;
    mysql^.free_me := true;
  end else
    FillChar(mysql^,Sizeof(mysql^),0);
  remember_connection(mysql^);
  mysql^.reconnect := true;                   (* Reconnect as default *)
  net := @mysql^.net;
  net^.fd := -1;                          (* If something goes wrong *)
  if host<>nil then my_host := host
  else begin
    hoststr := GetEnv('MYSQL_HOST');
    if length(hoststr)>0 then begin
      hoststr[length(hoststr)+1] := #0;
      my_host := @hoststr[1];
    end else
      my_host := nil;
  end;
  if (my_host = nil)or(my_host^ = #0) then my_host := LOCAL_HOST;

  (*
  ** Grab a socket and connect it to the server
  *)

  if (StrIComp(my_host,LOCAL_HOST)=0) and ((unix_socket<>nil) or (mysql_unix_port<>nil)) then begin
    if unix_socket=nil then
      my_unix_socket := mysql_unix_port
    else
      my_unix_socket := unix_socket;

    host_info := ER(CR_LOCALHOST_CONNECTION);
    //DBUG_PRINT("info",("Using UNIX sock '%s'",unix_socket));
    sock := socket(AF_UNIX,SOCK_STREAM,0);
    if sock = SOCKET_ERROR then begin
      net^.last_errno := CR_SOCKET_CREATE_ERROR;
      StrCopy(net^.last_error,ER(net^.last_errno));
      goto error;
    end;
    net^.fd := sock;
    opt := 1;
    setsockopt(sock, SOL_SOCKET, SO_KEEPALIVE, opt, sizeof(opt));
    FillChar(UNIX_addr,Sizeof(UNIX_addr),0);
    UNIX_addr.sun_family := AF_UNIX;
    StrCopy(UNIX_addr.sun_path, my_unix_socket);
    if connect(sock,UNIX_addr, sizeof(UNIX_addr)) <0 then begin
      //DBUG_PRINT("error",("Got error %d on connect to local server",ERRNO));
      net^.last_errno := CR_CONNECTION_ERROR;
      StrCopy(net^.last_error,ER(net^.last_errno));
      goto error;
    end
  end else begin
    if port = 0 then port := mysql_port; my_unix_socket := nil;
    host_info := @buff[0];
    StrFmt(host_info,ER(CR_TCP_CONNECTION),[my_host]);
    //DBUG_PRINT("info",("Server name: '%s'.  TCP sock: %d", host,port));
    sock := socket(AF_INET,SOCK_STREAM,0);
    if sock = SOCKET_ERROR then begin
      net^.last_errno := CR_IPSOCK_ERROR;
      StrCopy(net^.last_error,ER(net^.last_errno));
      goto error;
    end;
    net^.fd := sock;
    opt := 1;
    setsockopt(sock, SOL_SOCKET, SO_KEEPALIVE, opt, sizeof(opt));
    FillChar(sock_addr,sizeof(sock_addr),0);
    sock_addr.sin_family := AF_INET;

    (*
    ** The server name may be a host name or IP address
    *)

    ip_addr := inet_addr(my_host);
    if ip_addr <> INADDR_NONE then begin
      Move(ip_addr,sock_addr.sin_addr,sizeof(ip_addr));
    end else begin
      hp := gethostbyname(my_host);
      if hp = nil then begin
        net^.last_errno := CR_UNKNOWN_HOST;
        StrFmt(net^.last_error, ER(CR_UNKNOWN_HOST), [host, sock_errno]);
        goto error;
      end;
      sock_addr.sin_addr.s_addr := Longint(Pointer(hp^.h_addr^)^);
      //Move(hp^.h_addr^,sock_addr.sin_addr, hp^.h_length);
    end;
    sock_addr.sin_port := htons(port);
    if connect(sock,sock_addr, sizeof(sock_addr))<0 then begin
      //DBUG_PRINT("error",("Got error %d on connect to '%s'",ERRNO,host));
      net^.last_errno := CR_CONN_HOST_ERROR;
      StrFmt(net^.last_error,ER(CR_CONN_HOST_ERROR), [host, sock_ERRNO]);
      goto error;
    end;
  end;

{#if defined(SIGPIPE)
  (void) signal(SIGPIPE,SIG_IGN);
#endif}
  //DBUG_PRINT("info",("Connection socket %d",sock));
  if my_net_init(net^,sock)<>0 then
    goto error;
  (* Get version info *)
  mysql^.protocol_version := PROTOCOL_VERSION;    (* Assume this *)
  pkt_length := net_safe_read(mysql^);
  if pkt_length = packet_error then
    goto error;

  (* Check if version of protocoll matches current one *)

  mysql^.protocol_version := net^.buff^;
  //DBUG_DUMP("packet",(char*) net->buff,10);
  //DBUG_PRINT("info",("mysql protocol version %d, server=%d",
  //                   PROTOCOL_VERSION, mysql->protocol_version));
  if (mysql^.protocol_version <> PROTOCOL_VERSION)and
     (mysql^.protocol_version <> PROTOCOL_VERSION-1) then begin
    net^.last_errno := CR_VERSION_ERROR;
    StrFmt(net^.last_error, ER(CR_VERSION_ERROR), [mysql^.protocol_version,
            PROTOCOL_VERSION]);
    goto error;
  end;
  pend := Pointer(net^.buff); inc(pend);
  pend := strend(pend); inc(pend);
  mysql^.thread_id := uint4korr(pend);
  inc(pend,4);
  StrCopy(scramble_buff,pend);
  if pkt_length > (LongInt(pend)+9 - LongInt(net^.buff)) then begin
    inc(pend,9);
    mysql^.server_capabilities := uint2korr(pend);
    dec(pend,9);
  end;

  (* Save connection information *)
  if user=nil then my_user := '' else my_user := user;
  if my_passwd = nil then my_passwd := '';
  if my_multi_malloc([@mysql^.host_info,host_info,
                      @mysql^.host,my_host,
                      @mysql^.user,my_user,
                      @mysql^.passwd,my_passwd,
                      @mysql^.unix_socket,my_unix_socket,
                      @mysql^.server_version,LongInt(pend) - LongInt(net^.buff)]
                      ) = nil then begin
    net^.last_errno := CR_OUT_OF_MEMORY;
    StrCopy(net^.last_error, ER(net^.last_errno));
    goto error;
  end;
  StrCopy(mysql^.host_info,host_info);
  StrCopy(mysql^.host,my_host);
  StrCopy(mysql^.user,my_user);
  StrCopy(mysql^.passwd,my_passwd);
  if my_unix_socket <> nil then
    StrCopy(mysql^.unix_socket,my_unix_socket)
  else
    mysql^.unix_socket := nil;
  env := Pointer(net^.buff); inc(env);
  StrCopy(mysql^.server_version,env);
  mysql^.port := port;
  mysql^.client_flag := client_flag;
  //DBUG_PRINT("info",("Server version = '%s'",mysql->server_version));

  (* Send client information for access check *)
  client_flag := client_flag or CLIENT_CAPABILITIES;
  int2store(buff+0,client_flag);
  int3store(buff+2,max_allowed_packet);
  if (my_user<>nil)and(my_user^<>#0) then
    StrMake(buff+5,my_user,32)
  else
    read_user_name(buff+5);
  //DBUG_PRINT("info",("user: %s",buff+5));
  pend := scramble(StrEnd(buff+5)+1, scramble_buff, my_passwd,
                   (mysql^.protocol_version = 9));

  if (my_net_write(net^,Pointer(@buff),Word(pend)-Word(@buff))<>0) or (net_flush(net^)<>0) or
      (net_safe_read(mysql^) = packet_error) then
    goto error;
  //DBUG_PRINT("exit",("Mysql handler: %lx",mysql));
  //DBUG_RETURN(mysql);
  Result := mysql;
  exit;

error:
  //DBUG_PRINT("error",("message: %u (%s)",net->last_errno,net->last_error));
  end_server(mysql^);
  if mysql^.free_me then
    FreeMem(mysql,sizeof(mysql^));
  Result := nil;
end;


(**************************************************************************
** Set current database
**************************************************************************)

function mysql_select_db(mysql:PMYSQL;const db:PChar):Integer;
begin
  //DBUG_ENTER("mysql_select_db");
  //DBUG_PRINT("enter",("db: '%s'",db));

  Result := simple_command(mysql^,COM_INIT_DB,db,StrLen(db),false);
  if Result <> 0 then exit;
  StrDispose(mysql^.db);
  mysql^.db := StrNew(db);
end;

(*************************************************************************
** Send a QUIT to the server and close the connection
** If handle is alloced by mysql connect free it.
*************************************************************************)

procedure mysql_close(mysql:PMYSQL);
begin
  //DBUG_ENTER("mysql_close");
  if mysql <> nil then begin             (* Some simple safety *)
    if mysql^.net.fd >= 0 then begin
      free_old_query(mysql^);
      mysql^.status := MYSQL_STATUS_READY; (* Force command *)
      simple_command(mysql^,COM_QUIT,'',0,true);
      end_server(mysql^);
    end;
    FreeMem(mysql^.host_info,0);
    StrDispose(mysql^.db);
    mysql^.host_info := nil;
    mysql^.db := nil;
    if mysql^.free_me then
      FreeMem(mysql,Sizeof(mysql^));
  end;
end;


(**************************************************************************
** Do a query. If query returned rows, free old rows.
** Read data by mysql_store_result or by repeat call of mysql_fetch_row
**************************************************************************)

function mysql_query(mysql:PMYSQL;const query:PChar):Integer;
begin
  Result := mysql_real_query(mysql,query,StrLen(query));
end;


function mysql_real_query(mysql:PMYSQL;const query:PChar;len:Word):Integer;
var
  pos                   : PBYTE;
  field_count           : Word;
  fields                : PMYSQL_DATA;
begin
  //DBUG_ENTER("mysql_real_query");
  //DBUG_PRINT("enter",("handle: %lx",mysql));
  //DBUG_PRINT("query",("Query = \"%s\"",query));
  Result := -1;

  if simple_command(mysql^,COM_QUERY,query,len,true)<>0 then exit;
  len := net_safe_read(mysql^);
  if len = packet_error then exit;
  free_old_query(mysql^);                        (* Free old result *)
  pos := mysql^.net.buff;
  field_count := net_field_length(pos);
  if field_count = 0 then begin
    mysql^.affected_rows := net_field_length(pos);
    mysql^.insert_id :=     net_field_length(pos);
    if (Word(pos) < Word(mysql^.net.buff)+len)and(net_field_length(pos)<>0) then
      mysql^.info := Pointer(pos);
    Result := 0;
    exit;
  end;
  mysql^.extra_info := net_field_length(pos); (* Maybe number of rec *)
  fields := read_rows(mysql^,nil,5);
  if fields=nil then exit;
  mysql^.fields := unpack_fields(fields^,mysql^.field_alloc,field_count,false,
                                 mysql^.server_capabilities and CLIENT_LONG_FLAG<>0);
  if mysql^.fields = nil then exit;
  mysql^.status := MYSQL_STATUS_GET_RESULT;
  mysql^.field_count := field_count;
  Result := 0;
end;


(**************************************************************************
** Alloc result struct for buffered results. All rows are read to buffer.
** mysql_data_seek may be used.
**************************************************************************)

function mysql_store_result(mysql:PMYSQL):PMYSQL_RES;
var tmpres:PMYSQL_RES;
begin
  //DBUG_ENTER("mysql_store_result");
  Result := nil;
  if mysql^.fields = nil then exit;
  if mysql^.status <> MYSQL_STATUS_GET_RESULT then begin
    mysql^.net.last_errno := CR_COMMANDS_OUT_OF_SYNC;
    StrCopy(mysql^.net.last_error,ER(mysql^.net.last_errno));
    exit;
  end;
  mysql^.status := MYSQL_STATUS_READY;             (* server is ready *)
  Result := AllocMem(sizeof(MYSQL_RES)+sizeof(Word)*mysql^.field_count);
  if Result = nil then begin
    mysql^.net.last_errno := CR_OUT_OF_MEMORY;
    StrCopy(mysql^.net.last_error, ER(mysql^.net.last_errno));
    exit;
  end;
  result^.eof := True;                                (* Marker for buffered *)

  tmpres:=result;
  inc(tmpres);
  result^.lengths := Pointer(tmpres);

  result^.data := read_rows(mysql^,mysql^.fields,mysql^.field_count);
  if result^.data = nil then begin
    FreeMem(result,sizeof(MYSQL_RES)+sizeof(Word)*mysql^.field_count);
    Result := nil;
    exit;
  end;
  mysql^.affected_rows := result^.data^.rows;
  result^.row_count :=    result^.data^.rows;
  result^.data_cursor :=  result^.data^.data;
  result^.fields :=       mysql^.fields;
  result^.field_alloc :=  mysql^.field_alloc;
  result^.field_count :=  mysql^.field_count;
  result^.current_field := 0;
  result^.current_row := nil;                      (* Must do a fetch first *)
  mysql^.fields := nil;                            (* fields is now in result *)
end;


(**************************************************************************
** Alloc struct for use with unbuffered reads. Data is fetched by domand
** when calling to mysql_fetch_row.
** mysql_data_seek is a noop.
**
** No other queries may be specified with the same MYSQL handle.
** There shouldn't be much processing per row because mysql server shouldn't
** have to wait for the client (and will not wait more than 30 sec/packet).
**************************************************************************)

function mysql_use_result(mysql:PMYSQL):PMYSQL_RES;
var tmpres:PMYSQL_RES;
begin
  //DBUG_ENTER("mysql_use_result");

  Result := nil;
  if mysql^.fields=nil then exit;
  if mysql^.status <> MYSQL_STATUS_GET_RESULT then begin
    mysql^.net.last_errno := CR_COMMANDS_OUT_OF_SYNC;
    StrCopy(mysql^.net.last_error,ER(mysql^.net.last_errno));
    exit;
  end;
  result := AllocMem(sizeof(MYSQL_RES)+sizeof(Word)*mysql^.field_count);
  if result = nil then exit;

  tmpres:=result;
  inc(tmpres);
  result^.lengths := Pointer(tmpres);

  result^.row := AllocMem(sizeof(result^.row^[0])*(mysql^.field_count+1));
  if result^.row = nil then begin
    FreeMem(result,sizeof(MYSQL_RES)+sizeof(Word)*mysql^.field_count);
    result := nil;
    exit;
  end;
  result^.fields :=       mysql^.fields;
  result^.field_alloc :=  mysql^.field_alloc;
  result^.field_count :=  mysql^.field_count;
  result^.handle :=       mysql;
  result^.current_field := 0;
  result^.current_row :=  nil;
  mysql^.fields := nil;                      (* fields is now in result *)
  mysql^.status := MYSQL_STATUS_USE_RESULT;
end;



(**************************************************************************
** Return next field of the query results
**************************************************************************)

function mysql_fetch_field(res:PMYSQL_RES):PMYSQL_FIELD;
begin
  if res^.current_field >= res^.field_count then
    Result := nil
  else begin
    Result := res^.fields;
    inc(Result,res^.current_field);
    inc(res^.current_field);
  end;
end;


(**************************************************************************
**  Return next row of the query results
**************************************************************************)

function mysql_fetch_row(res:PMYSQL_RES):PMYSQL_ROW;
var
  error                 : Integer;
  tmp                   : PMYSQL_ROW;
begin
  if res^.data = nil then begin       (* Unbufferred fetch *)
    if not res^.eof then begin
      error := read_one_row(res^.handle^,res^.field_count,res^.row^,res^.lengths);
      if error=0 then begin
        inc(res^.row_count);
        res^.current_row := res^.row;
        result := res^.row;
        exit;
      end else begin
        res^.eof := true;
        res^.handle^.status := MYSQL_STATUS_READY;
      end;
    end;
    Result := nil;
    exit;
  end else begin
    if res^.data_cursor = nil then begin
      res^.current_row := nil;
      result := nil;
      exit;
    end;
    tmp := res^.data_cursor^.data;
    res^.data_cursor := res^.data_cursor^.next;
    res^.current_row := tmp;
    result := tmp;
  end;
end;

(**************************************************************************
** Get column lengths of the current row
** If one uses mysql_use_result, res->lengths contains the length information,
** else the lengths are calculated from the offset between pointers.
**************************************************************************)

function mysql_fetch_lengths(res:PMYSQL_RES):PWord;
var
  lengths, prev_length  : PWord;
  start                 : PBYTE;
  column                : PMYSQL_ROW;
  idx                   : Word;
begin
  Result := nil;
  column := res^.current_row;
  if column = nil then exit;                    (* Something is wrong *)
  if res^.data <> nil then begin
    start := nil;
    prev_length := nil;                         (* Keep gcc happy *)
    lengths := res^.lengths;
    for idx := 0 to res^.field_count do begin
      if column^[idx] = nil then begin
        lengths^ := 0;
      end else begin
        if start<>nil then                      (* Found end of prev string *)
          prev_length^ := LongInt(column^[idx])-LongInt(start)-1;
        start := Pointer(column^[idx]);
        prev_length := lengths;
      end;
      inc(lengths);
    end;
  end;
  Result := res^.lengths;
end;

(**************************************************************************
** Move to a specific row and column
**************************************************************************)

procedure mysql_data_seek(res:PMYSQL_RES;row:Word);
var
  tmp                   : PMYSQL_ROWS;
begin
  tmp := nil;
  //DBUG_PRINT("info",("mysql_data_seek(%d)",row));
  if res^.data <> nil then begin
    tmp := res^.data^.data;
    while (row<0) and (tmp<>nil) do begin
      dec(row); tmp := tmp^.next;
    end;
  end;
  res^.current_row := nil;
  res^.data_cursor := tmp;
end;

(*************************************************************************
** put the row or field cursor at the saved position.
** This dosen't restore any data. The next mysql_fetch_row or
** mysql_fetch_field will return the next row or field after the last used
*************************************************************************)

function mysql_row_seek(res:PMYSQL_RES;row:MYSQL_ROW_OFFSET):MYSQL_ROW_OFFSET;
begin
  result := MYSQL_ROW_OFFSET(res^.data_cursor);
  res^.current_row := nil;
  MYSQL_ROW_OFFSET(res^.data_cursor) := row;
end;


function mysql_field_seek(res:PMYSQL_RES;fieldnr:Word):MYSQL_FIELD_OFFSET;
begin
  result := res^.current_field;
  res^.current_field := fieldnr;
end;

(*****************************************************************************
** List all databases
*****************************************************************************)

function mysql_list_dbs(mysql:PMYSQL;const wild:PChar):PMYSQL_RES;
var
  buff                  : Array[0..99] of Char;
begin
  //DBUG_ENTER("mysql_list_dbs");
  Result := nil;
  append_wild(StrECopy(buff,'show databases'),buff+sizeof(buff),wild);
  if mysql_query(mysql,buff) < 0 then exit;
  Result := mysql_store_result(mysql);
end;


(*****************************************************************************
** List all tables in a database
** If wild is given then only the tables matching wild is returned
*****************************************************************************)

function mysql_list_tables(mysql:PMYSQL;const wild:PChar):PMYSQL_RES;
var
  buff                  : Array[0..99] of Char;
begin
  //DBUG_ENTER("mysql_list_tables");
  Result := nil;
  append_wild(StrECopy(buff,'show tables'),buff+sizeof(buff),wild);
  if mysql_query(mysql,buff) < 0 then exit;
  Result := mysql_store_result(mysql);
end;


(**************************************************************************
** List all fields in a table
** If wild is given then only the fields matching wild is returned
** Instead of this use query:
** show fields in 'table' like "wild"
**************************************************************************)

function mysql_list_fields(mysql:PMYSQL;const table,wild:PChar):PMYSQL_RES;
var
  res                   : PMYSQL_RES;
  query                 : PMYSQL_DATA;
  buff                  : Array[0..256] of Char;
  pend,my_wild          : PChar;
begin
  //DBUG_ENTER("mysql_list_fields");
  //DBUG_PRINT("enter",("table: '%s'  wild: '%s'",table,wild ? wild : ""));

  //LINT_INIT(query);
  Result := nil;
  if wild=nil then my_wild := '' else my_wild := wild;
  pend := strmake(strmake(buff,table,128)+1,my_wild,128);
  if simple_command(mysql^,COM_FIELD_LIST,buff,(pend-buff),true)<>0 then exit;
  query := read_rows(mysql^,nil,6);
  if query = nil then exit;
  free_old_query(mysql^);
  result := AllocMem(sizeof(MYSQL_RES));
  if res=nil then begin
    free_rows(query);
    exit;
  end;
  result^.field_alloc := mysql^.field_alloc;
  mysql^.fields := nil;
  result^.field_count := query^.rows;
  result^.fields := unpack_fields(query^,result^.field_alloc,
                                result^.field_count,true,
                                mysql^.server_capabilities and CLIENT_LONG_FLAG<>0);
  result^.eof:=true;
end;

(* List all running processes (threads) in server *)

function mysql_list_processes(mysql:PMYSQL):PMYSQL_RES;
var
  fields                : PMYSQL_DATA;
  field_count           : Word;
  pos                   : PBYTE;
begin
  //DBUG_ENTER("mysql_list_processes");

  //LINT_INIT(fields);
  Result := nil;
  if simple_command(mysql^,COM_PROCESS_INFO,nil,0,false)<>0 then exit;
  free_old_query(mysql^);
  pos := mysql^.net.buff;
  field_count := net_field_length(pos);
  fields := read_rows(mysql^,nil,5);
  if fields = nil then exit;
  mysql^.fields := unpack_fields(fields^,mysql^.field_alloc,field_count,false,
                                 mysql^.server_capabilities and CLIENT_LONG_FLAG<>0);
  if mysql^.fields = nil then exit;
  mysql^.status := MYSQL_STATUS_GET_RESULT;
  mysql^.field_count := field_count;
  Result := mysql_store_result(mysql);
end;


function mysql_create_db(mysql:PMYSQL;const db:PChar):Integer;
begin
  //DBUG_ENTER("mysql_createdb");
  //DBUG_PRINT("enter",("db: %s",db));
  Result := simple_command(mysql^,COM_CREATE_DB,db,StrLen(db),false);
end;


function mysql_drop_db(mysql:PMYSQL;const db:PChar):Integer;
begin
  //DBUG_ENTER("mysql_drop_db");
  //DBUG_PRINT("enter",("db: %s",db));
  Result := simple_command(mysql^,COM_DROP_DB,db,StrLen(db),false);
end;


function mysql_shutdown(mysql:PMYSQL):Integer;
begin
  //DBUG_ENTER("mysql_shutdown");
  Result := simple_command(mysql^,COM_SHUTDOWN,nil,0,false);
end;


function mysql_refresh(mysql:PMYSQL;options:Word):Integer;
var
  bits                  : Array[0..0] of Byte;
begin
  //DBUG_ENTER("mysql_refresh");
  bits[0] := options;
  Result := simple_command(mysql^,COM_REFRESH,Pointer(@bits),1,false);
end;

function mysql_kill(mysql:PMYSQL;pid:Cardinal):Integer;
var
  buff                  : Array[0..3] of Byte;
begin
  //DBUG_ENTER("mysql_kill");
  int4store(@buff,pid);
  Result := simple_command(mysql^,COM_PROCESS_KILL,Pointer(@buff),4,false);
end;


function mysql_dump_debug_info(mysql:PMYSQL):Integer;
begin
  //DBUG_ENTER("mysql_dump_debug_info");
  Result := simple_command(mysql^,COM_DEBUG,nil,0,false);
end;

function mysql_stat(mysql:PMYSQL):PChar;
begin
  //DBUG_ENTER("mysql_stat");
  if simple_command(mysql^,COM_STATISTICS,nil,0,false)<>0 then begin
    Result := mysql^.net.last_error;
    exit;
  end;
  if mysql^.net.buff^ = 0 then begin
    mysql^.net.last_errno := CR_WRONG_HOST_INFO;
    StrCopy(mysql^.net.last_error, ER(mysql^.net.last_errno));
    Result := mysql^.net.last_error;
  end else
    Result := Pointer(mysql^.net.buff);
end;


function mysql_get_server_info(mysql:PMYSQL):PChar;
begin
  Result := mysql^.server_version;
end;


function mysql_get_host_info(mysql:PMYSQL):PChar;
begin
  Result := mysql^.host_info;
end;


function mysql_get_proto_info(mysql:PMYSQL):Word;
begin
  Result := mysql^.protocol_version;
end;

function mysql_get_client_info:PChar;
begin
  Result := MYSQL_SERVER_VERSION;
end;


(****************************************************************************
** Some support functions
****************************************************************************)

(*
** Add escape characters to a string (blob?) to make it suitable for a insert
** to should at least have place for length*2+1 chars
*)

function mysql_escape_string(sto:PChar;const from:PChar;from_length:Word):Word;
var
  to_start, pend, pos   : PChar;
begin
  to_start := sto;
  pend := from+from_length; pos := from;
  while pos <> pend do begin
    case pos^ of
      #0 : begin                        (* Must be escaped for 'mysql' *)
        sto^ := '\'; inc(sto);
        sto^ := '0'; inc(sto);
      end;
      #10: begin                        (* Must be escaped for logs *)
        sto^ := '\'; inc(sto);
        sto^ := 'n'; inc(sto);
      end;
      #13: begin
        sto^ := '\'; inc(sto);
        sto^ := 'r'; inc(sto);
      end;
      '\': begin
        sto^ := '\'; inc(sto);
        sto^ := '\'; inc(sto);
      end;
      '''': begin
        sto^ := '\'; inc(sto);
        sto^ := ''''; inc(sto);
      end;
      '"': begin                        (* Better safe than sorry *)
        sto^ := '\'; inc(sto);
        sto^ := '"'; inc(sto);
      end;
      else begin
        sto^ := pos^; inc(sto);
      end;
    end;
    inc(pos);
  end;
  sto^ := #0;
  Result := sto - to_start;
end;

function mysql_unescape_string(sto:PChar;const from:PChar):Word;
var
  to_start, pos         : PChar;
begin
  to_start := sto; pos := from;
  while pos^ <> #0 do begin
    if pos^ = '\' then begin
      inc(pos);
      case pos^ of
        #0      : break;
        '0'     : begin
          sto^ := #0; inc(sto);
        end;
        'n'     : begin
          sto^ := #10; inc(sto);
        end;
        'r'     : begin
          sto^ := #13; inc(sto);
        end;
        else begin
          sto^ := pos^; inc(sto);
        end;
      end;
    end else begin
      sto^ := pos^; inc(sto);
    end;
    inc(pos);
  end;
  sto^ := #0;
  Result := sto - to_start;
end;

procedure randominit2(var rand:rand_struct; seed1, seed2: Cardinal); {&Uses eax, ebx, edx}
assembler;
asm
  mov   ebx, rand
  mov   eax, seed1
  sub   edx, edx
  div   rand_struct([ebx]).max_value
  mov   rand_struct([ebx]).seed, edx
  mov   eax, seed2
  sub   edx, edx
  div   rand_struct([ebx]).max_value
  mov   rand_struct([ebx]).seed2, edx
end;


procedure randominit(var rand:rand_struct;seed1,seed2:Cardinal);
begin                                           (* For mysql 3.21.# *)
  rand.max_value := $3FFFFFFF;
  randominit2(rand, seed1, seed2);
  rand.max_value_dbl := rand.max_value;
  //rand.seed := seed1 mod rand.max_value;
  //rand.seed2 := seed2 mod rand.max_value;
end;

procedure old_randominit2(var rand:rand_struct; seed: Cardinal); {&Uses eax,ebx,edx}
assembler;
asm
  mov   ebx, rand
  mov   eax, seed
  sub   edx, edx
  div   rand_struct([ebx]).max_value
  mov   rand_struct([ebx]).seed, edx
  shr   edx, 1
  mov   rand_struct([ebx]).seed2, edx
end;


procedure old_randominit(var rand:rand_struct;seed:Cardinal);
begin                                            (* For mysql 3.20.# *)
  rand.max_value := $01FFFFFF;
  old_randominit2(rand, seed);
  rand.max_value_dbl := rand.max_value;
  //rand.seed := seed mod rand.max_value;
  //rand.seed2 := rand.seed div 2;
end;

function rnd2(var rand:rand_struct):Cardinal; {&Uses ebx, ecx, edx}
assembler;
asm
  mov   ebx, rand
  mov   eax, rand_struct[ebx].seed
  mov   ecx, 3
  mul   ecx
  add   eax, rand_struct[ebx].seed2
  adc   edx, 0
  div   rand_struct[ebx].max_value
  mov   rand_struct[ebx].seed, edx

  mov   eax, edx
  mov   ecx, eax
  sub   edx, edx
  add   eax, rand_struct[ebx].seed2
  adc   edx, 0
  add   eax, 33
  adc   edx, 0
  div   rand_struct[ebx].max_value
  mov   rand_struct[ebx].seed2, edx

  mov   eax, ecx
end;

function rnd(var rand:rand_struct):double;
begin
  Result := rnd2(rand) / rand.max_value_dbl;
  //rand.seed := (rand.seed*3 + rand.seed2) mod rand.max_value;
  //rand.seed2 := (rand.seed + rand.seed2+33) mod rand.max_value;
  //Result := rand.seed/rand.max_value_dbl;
end;

procedure hash_password(var res;const password:PChar);
var
  result                : Array[0..1] of Cardinal absolute res;
  nr,add,nr2            : Cardinal;
  tmp                   : Cardinal;
  passwd                : PChar;
begin
  nr := 1345345333; add := 7; nr2 := $12345671; passwd := password;
  while passwd^<>#0 do begin
    if (passwd^<>' ')and(passwd^<>#9) then begin
      tmp := Ord(passwd^);
      nr := nr xor ((((nr and 63)+add)*tmp)+(nr shl 8));
      inc(nr2,(nr2 shl 8)xor nr);
      inc(add,tmp);
    end;
    inc(passwd);
  end;
  result[0] := nr and $7FFFFFFF;
  result[1] := nr2 and $7FFFFFFF;
end;

procedure make_scrambled_password(pto:PChar;const password:PChar);
var
  hash_res              : Array[0..1] of Cardinal;
begin
  hash_password(hash_res,password);
  StrFmt(pto,'%8.8x%8.8x',[hash_res[0],hash_res[1]]);
end;

function char_val(X:Char):Integer; inline;
begin
  if (X>='0') and (X<='9') then Result := Ord(X)-Ord('0') else
  if (X>='A') and (X<='Z') then Result := Ord(X)-Ord('A')+10 else
                                Result := Ord(X)-Ord('a')+10;
end;

(*
** This code assumes that len(password) is divideable with 8 and that
** res is big enough (2 in mysql)
*)

procedure get_salt_from_password(var result;const password:PChar);
var
  res                   :^Cardinal;
  passwd                : PChar;
  val                   : Cardinal;
  i                     : Word;
begin
  res := Pointer(@result); res^ := 0; inc(res); res^ := 0; dec(res);
  if password<>nil then begin
    passwd := password;
    while passwd^<>#0 do begin
      val := 0;
      for i := 0 to 7 do begin
        val := (val shl 4)+char_val(passwd^);
        inc(passwd);
      end;
      res^ := val; inc(res);
    end;
  end;
end;

(*
 * Genererate a new message based on message and password
 * The same thing is done in client and server and the results are checked.
 *)

function scramble(pto:PChar;const msg,passwd:PChar;old_ver:my_bool):PChar;
var
  rand                  : rand_struct;
  hash_pass,hash_msg    : Array[0..1] of Cardinal;
  xto, x_to_start, xmsg : PByte;
  //to_start,message      : PChar;
  extra                 : Byte;
begin
  //message := msg; to_start := pto;
  xmsg := Pointer(msg); xto := Pointer(pto); x_to_start := xto;
  if (passwd<>nil)and(passwd^<>#0) then begin
    hash_password(hash_pass,passwd);
    hash_password(hash_msg, msg);
    if old_ver then
      old_randominit(rand,hash_pass[0] xor hash_msg[0])
    else
      randominit(rand,hash_pass[0] xor hash_msg[0],
                      hash_pass[1] xor hash_msg[1]);

    while xmsg^ <> 0 do begin
      inc(xmsg);
      xto^ := floor(rnd(rand)*31.0)+64;
      inc(xto);
    end;
    if not old_ver then begin
      extra := floor(rnd(rand)*31);
      while x_to_start <> xto do begin
        x_to_start^ := x_to_start^ xor extra;
        inc(x_to_start);
      end;
    end;
    {while message^<>#0 do begin
      inc(message);
      pto^ := Chr(floor(rnd(rand)*31)+64);
      inc(pto);
    end;
    if not old_ver then begin   (* Make it harder to break *)
      extra := floor(rnd(rand)*31);
      while to_start<pto do begin
        to_start^ := Chr(Ord(to_start^) xor extra);
        inc(to_start);
      end;
    end;}
  end;
  {pto^ := #0;
  Result := pto;}
  xto^ := 0;
  Result := Pointer(xto);
end;


function check_scramble(const scramble, msg:PChar;var salt;old_ver:my_bool):Boolean;
var
  rand                  : rand_struct;
  hash_pass             : Array[0..1] of Cardinal absolute salt;
  hash_message          : Array[0..1] of Cardinal;
  buff                  : Array[0..15] of Char;
  pto,pos,scram         : PChar;
  extra                 : Byte;
begin
  hash_password(hash_message,msg);
  if old_ver then
    old_randominit(rand,hash_pass[0] xor hash_message[0])
  else
    randominit(rand,hash_pass[0] xor hash_message[0],
                    hash_pass[1] xor hash_message[1]);
  pto := buff; pos := scramble;
  while pos^<>#0 do begin
    pto^ := Chr(floor(rnd(rand)*31)+64);
    inc(pto);
  end;
  if old_ver then
    extra := 0
  else
    extra := floor(rnd(rand)*31);
  pto := buff; scram := scramble;

  while scram^<>#0 do begin
    if Ord(scram^) <> (Ord(pto^) xor extra) then begin
      Result := true;
      exit;
    end;
    inc(scram); inc(pto);
  end;
  Result := false;
end;

procedure init_client_errs;
{const
  client_errors         : Array[0..15] of PChar = (
    'Unknown MySQL error',
    'Can''t create UNIX socket',
    'Can''t connect to local MySQL server',
    'Can''t connect to MySQL server on %s (%d)',
    'Can''t create IP socket',
    'Unknown MySQL Server Host (%s) (%d)',
    'MySQL server has gone away',
    'Protocol mismatch. Server Version = %d Client Version = %d',
    'MySQL client got out of memory',
    'Wrong host info',
    'Localhost via UNIX socket',
    '%s via TCP/IP',
    'Error in server handshake',
    'Lost connection to MySQL server during query',
    'Commands out of sync;  You can''t run this command now',
    nil
  );}
begin
  errmsg[CLIENT_ERRMAP] := Pointer(@client_errors);
end;

end.
