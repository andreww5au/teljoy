unit netMySQL;
{&Delphi+}
(* Copyright Abandoned 1996 TCX DataKonsult AB & Monty Program KB & Detron HB
   This file is public domain and comes with NO WARRANTY of any kind *)

(* Write and read of logical packets to/from socket
** Writes are cached into net_buffer_length big packets.
** Read packets are reallocated dynamicly when reading big packets.
** Each logical packet has the following pre-info:
** 3 byte length & 1 byte package-number.
*)
interface
uses Use32, NetLib;

const
  MYSQL_ERRMSG_SIZE     = 200;
  NET_READ_TIMEOUT      = 30;                   (* Timeout on read *)
  NET_WRITE_TIMEOUT     = 60;                   (* Timeout on write *)
  NET_WAIT_TIMEOUT      = 8*60*60;              (* Wait for new query *)
  packet_error          = -1;

type
  PNET                  =^NET;
  NET                   = record
    fd                  : Integer;
    fcntl               : Integer;
    buff, buff_end      : PBYTE;
    write_pos           : PBYTE;
    last_error          : Array[0..MYSQL_ERRMSG_SIZE-1] of Char;
    last_errno          : Word;
    max_packet,timeout  : Word;
    pkt_nr              : Word;
    error, return_errno : Boolean;
  end;

(*
** Give error if a too big packet is found
** The server can change this with the -O switch, but because the client
** can't normally do this the client should have a bigger max-buffer.
*)
const
  max_allowed_packet    : Cardinal      = 1024 * 1024;
  net_buffer_length     : Cardinal      = 8192; (* Default length. Enlarged if necessary *)

procedure net_new_transaction(var net:NET); inline; begin net.pkt_nr := 0 end;

function  my_net_init(var net:NET;fd:Integer):Integer;
procedure net_end(var net:NET);
procedure net_clear(var net:NET);
function  net_flush(var net:NET):Integer;
function  my_net_write(var net:NET;const packet:PBYTE;len:Word):Integer;
function  net_write_command(var net:NET;command:Byte;const packet:PBYTE;len:Word):Integer;
function  net_real_write(var net:NET;const packet:PBYTE;len:Word):Integer;
function  my_net_read(var net:NET):Word;

implementation
uses SysUtils;

const
{$IFDEF OS2}
  EAGAIN                = SOCEINPROGRESS;
  EINTR                 = SOCEINTR;
{$ELSE}
  EAGAIN                = WSAEINPROGRESS;
  EINTR                 = WSAEINTR;
{$ENDIF}

function raw_net_read(A:Integer;var B;C:Integer):Integer; inline; begin Result := recv(A,B,C,0) end;
function raw_net_write(A:Integer;var B;C:Integer):Integer; inline; begin Result := send(A,B,C,0) end;

procedure int2store(var T;A:Word);
var
  Ta                    : Array[0..1] of Byte absolute T;
begin
  Ta[0] := A and $FF;
  Ta[1] := (A shr 8) and $FF;
end;

procedure int3store(var T;A:Word);
var
  Ta                    : Array[0..2] of Byte absolute T;
begin
  Ta[0] := A and $FF;
  Ta[1] := (A shr 8) and $FF;
  Ta[2] := (A shr 16) and $FF;
end;

function uint3korr(var A:Array of Byte):Word;
var
  Aa                    : Array[0..2] of Byte absolute A;
begin
  Result := Aa[0] + (Aa[1] + (Aa[2] shl 8))shl 8
end;

function test(a:Integer):Integer; inline;
begin if a<>0 then Result := 1 else Result := 0 end;

//extern uint test_flags;                 /* QQ */

function net_write_buff(var net:NET;const packet:PByte;len:Word):Integer; forward;


        (* Init with packet info *)

function my_net_init;
begin
  net.buff := AllocMem(net_buffer_length);
  if net.buff=nil then begin
    Result := 1;
    exit;
  end;

  if net_buffer_length > max_allowed_packet then max_allowed_packet := net_buffer_length;
  net.buff_end := net.buff;
  net.max_packet := net_buffer_length;
  inc(net.buff_end,net_buffer_length);
  net.fd := fd;
  net.error := false;
  net.return_errno := false;
  net.timeout := NET_READ_TIMEOUT;                        (* Timeout for read *)
  net.pkt_nr := 0;
  net.write_pos := net.buff;
  net.last_error[0] := #0;
  Result := 0;
end;

procedure net_end(var net:NET);
begin
  if net.buff <> nil then begin
    FreeMem(net.buff,net_buffer_length);
    net.buff := nil;
  end;
end;

        (* Remove unwanted characters from connection *)

procedure net_clear(var net:NET);
var
  arg                   : Word;
begin
  arg := 1; soioctl(net.fd,FIONBIO,arg,SizeOf(arg));
  while (raw_net_read(net.fd,net.buff^,net.max_packet) > 0) do;
  arg := 0; soioctl(net.fd,FIONBIO,arg,SizeOf(arg));
  net.pkt_nr := 0;                                (* Ready for new command *)
  net.write_pos := net.buff;
end;

        (* Flush write_buffer if not empty. *)

function net_flush(var net:NET):Integer;
var
  error                 : Integer;
begin
  error := 0;
  if net.buff <> net.write_pos then begin
    error := net_real_write(net,net.buff,Word(net.write_pos) - Word(net.buff));
    net.write_pos := net.buff;
  end;
  Result := error;
end;


(*****************************************************************************
** Write something to server/clinet buffer
*****************************************************************************)


(*
** Write a logical packet with packet header
** Format: Packet length (3 bytes), packet number(1 byte)
*)

function my_net_write(var net:NET;const packet:PBYTE;len:Word):Integer;
var
  buff                  : Array[0..3] of Byte;
begin
  int3store(buff,len);
  buff[3] := net.pkt_nr; inc(net.pkt_nr);
  if net_write_buff(net,@buff,4)<>0 then
    Result := 1
  else
    Result := net_write_buff(net,packet,len);
end;

function net_write_command(var net:NET;command:Byte;const packet:PBYTE;len:Word):Integer;
var
  buff                  : Array[0..4] of Byte;
  length                : Word;
begin
  length := len+1;                            (* One extra byte for command *)

  int3store(buff,length);
  buff[3] := net.pkt_nr; inc(net.pkt_nr);
  buff[4] := command;
  if net.buff = nil then begin
                                               (* If net not initiated *)
    Result := test(net_real_write(net,@buff,5) or
                   net_real_write(net,packet,len));
  end else
  if net_write_buff(net,@buff,5)<>0 then
    Result := 1
  else
    Result := test(net_write_buff(net,packet,len) or net_flush(net));
end;

function net_write_buff(var net:NET;const packet:PBYTE;len:Word):Integer;
var
  left_length           : Word;
  pkt                   : PBYTE;
begin
  if net_real_write(net,packet,len)<>0 then begin
    Result := 1;
    exit;
  end else begin
    Result := 0;
    exit;
  end;

  pkt := packet;
  left_length := Word(net.buff_end) - Word(net.write_pos);
  while len > left_length do begin
    move(pkt^,net.write_pos^,left_length);
    if net_real_write(net,net.buff,net.max_packet)<>0 then begin
      Result := 1;
      exit;
    end;
    net.write_pos := net.buff;
    inc(pkt,left_length);
    dec(len,left_length);
    left_length := net.max_packet;
  end;
  move(pkt^,net.write_pos^,len);
  inc(net.write_pos,len);
  Result := 0;
end;


function net_real_write(var net:NET;const packet:PBYTE;len:Word):Integer;
var
  length,errno          : Integer;
  ppos,pend             : PBYTE;
  alarmed               : Boolean;
begin
  alarmed := False;

  ppos := packet; pend := ppos; inc(pend,len);
  while ppos <> pend do begin
    length := raw_net_write(net.fd,ppos^,Word(pend)-Word(ppos));
    if length <= 0 then begin
      errno := sock_errno;
      if ((errno = EAGAIN) or (errno = EINTR) or (errno = EWOULDBLOCK) or (length = 0)) and not alarmed then begin
        alarmed := True;
        continue;
      end;
      if (errno = EINTR) then begin
        //DBUG_PRINT("warning",("Interrupted write. Retrying..."));
        continue;
      end;
      break;
    end;
    inc(ppos,length);
  end;
  Result := test(Word(ppos)-Word(pend));
end;

(*****************************************************************************
** Read something from server/clinet
*****************************************************************************)

const
  IO_SIZE = 4096;

function my_net_read(var net:NET):Word;
var
  ppos,buff             : PBYTE;
  mbuff                 : Array[0..3] of Byte;
  wrong_packet_nr       : Byte;
  len,remain,pkt_len    : Word;
  length,i,errno        : Integer;
  alarmed,error_packet  : Boolean;
label abort;
begin
  alarmed := False;
  error_packet := False;

  wrong_packet_nr := 0;
  len := packet_error;
  remain := 4;
  ppos := net.buff;                        (* net->packet -4 *)
  for i := 0 to 1 do begin
    while remain > 0 do begin
      length := raw_net_read(net.fd,ppos^,remain);
      if length <= 0 then begin
        errno := sock_errno;
        if ((errno = EAGAIN) or (errno = EINTR) or (errno = EWOULDBLOCK) or (length = 0)) and not alarmed then begin
          alarmed := True;
          continue;
        end;
        if (errno = EINTR) then begin
          //DBUG_PRINT("warning",("Interrupted read. Retrying..."));
          continue;
        end;
        //DBUG_PRINT("error",("Couldn't read packet: remain: %d  errno: %d  length: %d  alarmed: %d", remain,errno,length,alarmed));
        len := packet_error;
        goto abort;
      end;
      dec(remain,length);
      inc(ppos,length);
    end;
    if (i = 0) then begin
                                        (* First parts is packet length *)
      move(net.buff^,mbuff,4);
      len := uint3korr(mbuff);
      if len >= max_allowed_packet then begin
        //DBUG_PRINT("error",("Packet too large (%ld)",len));
        //fprintf(stderr,"Packet too large (%ld)\n", len);
        Result := packet_error;         (* Return error *)
        exit;
      end;
      if mbuff[3] <> net.pkt_nr then begin
        error_packet := True;              (* Probably error out of sync *)
        wrong_packet_nr := net.pkt_nr;
        net.pkt_nr := mbuff[3];
      end else
        inc(net.pkt_nr);

      if len >= net.max_packet then begin
                                        (* Alloc bigger package *)
        pkt_len := (len+IO_SIZE) and not(IO_SIZE-1);
        //buff := ReAllocMem(net.buff,net.max_packet,pkt_len);
        buff := AllocMem(pkt_len);
        if buff=nil then begin
          len := packet_error;
          break;
        end;
        Move(net.buff^,buff^,net.max_packet);
        FreeMem(net.buff,net.max_packet);
        net.buff := buff;
        net.write_pos := buff;
        net.buff_end := buff;
        net.max_packet := pkt_len;
        inc(net.buff_end,pkt_len);
      end;
      ppos := net.buff;
      remain := len;
    end;
  end;
  if error_packet and (net.buff^ <> 255) then begin
    //DBUG_PRINT("error",("Packets out of order (Found: %d, expected %d)\n",
    //                    (int) (uchar) net->pkt_nr,(int) wrong_packet_nr));
    //fprintf(stderr,"Packets out of order (Found: %d, expected %d)\n",
    //        (int) (uchar) net->pkt_nr,(int) wrong_packet_nr);
    len := packet_error;
  end;
abort:
  ppos^ := 0;                             (* Safeguard *)
  Result := len;
end;

end.
