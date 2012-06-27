Unit NetLib;
{&Delphi+,Use32-}
(****************************************************************************)
(*                                                                          *)
(*  NETLIB FOR OS/2 AND WIN32 --- CROSS PLATFORM SOCKET LIBRARY FOR PASCAL  *)
(*                                                                          *)
(*          COPYRIGHT 1998 ANTONY T CURTIS   ALL RIGHTS RESERVED            *)
(*          antony.curtis@olcs.net           http://nuts.ml.org/            *)
(*                                                                          *)
(*  USAGE LICENSE : AUTHOR MUST BE PROPERLY ACKNOWLEDGED IN PRODUCTS WHICH  *)
(*   MAKE USE OF THIS CODE. NO WARRANITES EITHER EXPRESSED OR IMPLIED ARE   *)
(*     APPLICABLE AS TO THE FITNESS OF THIS CODE - IT IS SUPPLIED AS IS     *)
(*                                                                          *)
(*          SUPPORT IS SUPPLIED AT THE DISCRETION OF THE AUTHOR             *)
(*                                                                          *)
(****************************************************************************)

interface

uses Use32,
{$IFDEF OS2}
OS2Def; {&CDecl+}
{$ELSE}
Windows; {&StdCall+}
{$ENDIF}

Const
  Max_Alias                     = 4;
  PZERO                         = 0;
  BSD                           = 43;

  MAXHOSTNAMELEN                = 120;
  MAXPATHLEN                    = 80;
  MAXSocketS                    = 2048;
  SOCKET_ERROR                  = -1;

  SIGALRM                       = 0;            (* Pah! Why not... I suppose I can make a signals unit... *)

  SOMAXCONN                     = 5;            (* Maximum queue length specifiable by listen. *)
  BUFSIZ                        = 4096;

  _MAX_ALIASES                  = 35;
  _MAX_ADDRS                    = 35;
  _MAXLINELEN                   = 1024;
  _HOSTBUFSIZE                  = BUFSIZ + 1;


Const
(*
 * Protocols
 *)
  IPPROTO_IP                    = 0;               (* dummy for IP *)
  IPPROTO_ICMP                  = 1;               (* control message protocol *)
  IPPROTO_GGP                   = 3;               (* gateway^2 (deprecated) *)
  IPPROTO_TCP                   = 6;               (* tcp *)
  IPPROTO_EGP                   = 8;               (* exterior gateway protocol *)
  IPPROTO_PUP                   = 12;              (* pup *)
  IPPROTO_UDP                   = 17;              (* user datagram protocol *)
  IPPROTO_IDP                   = 22;              (* xns idp *)
{$IFDEF WINDOWS}
  IPPROTO_ND                    = 77;              (* UNOFFICIAL net disk proto *)
{$ENDIF}

  IPPROTO_RAW                   = 255;             (* raw IP packet *)
  IPPROTO_MAX                   = 256;

// Port/socket numbers: network standard functions
  IPPORT_ECHO                   = 7;
  IPPORT_DISCARD                = 9;
  IPPORT_SYSTAT                 = 11;
  IPPORT_DAYTIME                = 13;
  IPPORT_FTP                    = 21;
  IPPORT_TELNET                 = 23;
  IPPORT_SMTP                   = 25;
  IPPORT_TIMESERVER             = 37;
  IPPORT_NAMESERVER             = 42;
  IPPORT_WHOIS                  = 43;
  IPPORT_MTP                    = 57;

// Port/socket numbers: host specific functions
  IPPORT_TFTP                   = 69;
  IPPORT_RJE                    = 77;
  IPPORT_FINGER                 = 79;
  IPPORT_TTYLINK                = 87;
  IPPORT_SUPDUP                 = 95;

// UNIX TCP sockets
  IPPORT_EXECSERVER             = 512;
  IPPORT_LOGINSERVER            = 513;
  IPPORT_CMDSERVER              = 514;
  IPPORT_EFSSERVER              = 520;

// UNIX UDP sockets
  IPPORT_BIFFUDP                = 512;
  IPPORT_WHOSERVER              = 513;
  UPPORT_ROUTESERVER            = 520;  // 520+1 also used

(*
 * Ports < IPPORT_RESERVED are reserved for
 * privileged processes (e.g. root).
 * Ports > IPPORT_USERRESERVED are reserved
 * for servers, not necessarily privileged.
 *)
  IPPORT_RESERVED               = 1024;
  IPPORT_USERRESERVED           = 5000;

(*
 * Link numbers
 *)
  IMPLINK_IP                    = 155;
  IMPLINK_LOWEXPER              = 156;
  IMPLINK_HIGHEXPER             = 158;

(*
 * Definitions of bits in internet address integers.
 * On subnets, the decomposition of addresses to host and net parts
 * is done according to subnet mask, not the masks here.
 *)
  IN_CLASSA_NET                 = $ff000000;
  IN_CLASSA_NSHIFT              = 24;
  IN_CLASSA_HOST                = $00ffffff;
  IN_CLASSA_MAX                 = 128;

  IN_CLASSB_NET                 = $ffff0000;
  IN_CLASSB_NSHIFT              = 16;
  IN_CLASSB_HOST                = $0000ffff;
  IN_CLASSB_MAX                 = 65536;

  IN_CLASSC_NET                 = $ffffff00;
  IN_CLASSC_NSHIFT              = 8;
  IN_CLASSC_HOST                = $000000ff;

  INADDR_ANY                    = $00000000;
  INADDR_BROADCAST              = $ffffffff;       (* must be masked *)
  INADDR_NONE                   = $ffffffff;            (* -1 return *)

  IN_LOOPBACKNET                = 127;                  (* official! *)

(*
 * Internet address (a structure for historical reasons)
 *)
Type
  in_addr                       = record
    s_addr                      : ULong;
  end;

(*
 * Socket address, internet style.
 *)
  sockaddr_in                   = record
    sin_family                  : UShort;
    sin_port                    : UShort;
    sin_addr                    : in_addr;
    sin_zero                    : array[0..7] of byte;
  end;

(*
 * Definitions for UNIX IPC domain.
 *)
  sockaddr_un                   = record
    sun_family                  : UShort; (* AF_UNIX *)
    sun_path                    : Array[0..107] of Char; (* path name (gag) *)
  end;

(*
 * Structure used for manipulating linger option.
 *)
  linger                        = record
    l_onoff                     : Integer;
    l_linger                    : Integer;
  end;

(*
 * Options for use with getsockopt at the IP level.
 *)
Const
  IP_OPTIONS                    = 1;               (* set/get IP per-packet options *)

(*
 * Definitions related to Sockets: types, address families, options.
 *)

(*
 * Types
 *)
Const
  SOCK_STREAM                   = 1;               (* stream Socket *)
  SOCK_DGRAM                    = 2;               (* datagram Socket *)
  SOCK_RAW                      = 3;               (* raw-protocol interface *)
  SOCK_RDM                      = 4;               (* reliably-delivered message *)
  SOCK_SEQPACKET                = 5;               (* sequenced packet stream *)

(*
 * Option flags per-Socket.
 *)
  SO_DEBUG                      = $0001;           (* turn on debugging info recording *)
  SO_ACCEPTCONN                 = $0002;           (* Socket has had listen() *)
  SO_REUSEADDR                  = $0004;           (* allow local address reuse *)
  SO_KEEPALIVE                  = $0008;           (* keep connections alive *)
  SO_DONTROUTE                  = $0010;           (* just use interface addresses *)
  SO_BROADCAST                  = $0020;           (* permit sending of broadcast msgs *)
  SO_USELOOPBACK                = $0040;           (* bypass hardware when possible *)
  SO_LINGER                     = $0080;           (* linger on close if data present *)
  SO_OOBINLINE                  = $0100;           (* leave received OOB data in line *)

(*
 * Additional options, not kept in so_options.
 *)
  SO_SNDBUF                     = $1001;           (* send buffer size *)
  SO_RCVBUF                     = $1002;           (* receive buffer size *)
  SO_SNDLOWAT                   = $1003;           (* send low-water mark *)
  SO_RCVLOWAT                   = $1004;           (* receive low-water mark *)
  SO_SNDTIMEO                   = $1005;           (* send timeout *)
  SO_RCVTIMEO                   = $1006;           (* receive timeout *)
  SO_ERROR                      = $1007;           (* get error status and clear *)
  SO_TYPE                       = $1008;           (* get Socket type *)

(*
 * Level number for (get/set)sockopt() to apply to Socket itself.
 *)
   SOL_SOCKET                   = $ffff;           (* options for Socket level *)

(*
 * Address families.
 *)
   AF_UNSPEC                    = 0;               (* unspecified *)
   AF_UNIX                      = 1;               (* local to host (pipes, portals) *)
   AF_INET                      = 2;               (* internetwork: UDP, TCP, etc. *)
   AF_IMPLINK                   = 3;               (* arpanet imp addresses *)
   AF_PUP                       = 4;               (* pup protocols: e.g. BSP *)
   AF_CHAOS                     = 5;               (* mit CHAOS protocols *)
   AF_NS                        = 6;               (* XEROX NS protocols *)
   AF_NBS                       = 7;               (* nbs protocols *)
   AF_ECMA                      = 8;               (* european computer manufacturers *)
   AF_DATAKIT                   = 9;               (* datakit protocols *)
   AF_CCITT                     = 10;              (* CCITT protocols, X.25 etc *)
   AF_SNA                       = 11;              (* IBM SNA *)
   AF_DECnet                    = 12;              (* DECnet *)
   AF_DLI                       = 13;              (* Direct data link interface *)
   AF_LAT                       = 14;              (* LAT *)
   AF_HYLINK                    = 15;              (* NSC Hyperchannel *)
   AF_APPLETALK                 = 16;              (* Apple Talk *)
   AF_NB                        = 17;              (* Netbios *)
   AF_NETBIOS                   = AF_NB;
{$IFDEF WINDOWS}
   AF_VOICEVIEW                 = 18;              (* VoiceView *)
   AF_MAX                       = 19;
{$ELSE}
   AF_OS2                       = AF_UNIX;
   AF_MAX                       = 18;
{$ENDIF}

(*
 * Protocol families, same as address families for now.
 *)
   PF_UNSPEC                    = AF_UNSPEC;
   PF_UNIX                      = AF_UNIX;
   PF_INET                      = AF_INET;
   PF_IMPLINK                   = AF_IMPLINK;
   PF_PUP                       = AF_PUP;
   PF_CHAOS                     = AF_CHAOS;
   PF_NS                        = AF_NS;
   PF_NBS                       = AF_NBS;
   PF_ECMA                      = AF_ECMA;
   PF_DATAKIT                   = AF_DATAKIT;
   PF_CCITT                     = AF_CCITT;
   PF_SNA                       = AF_SNA;
   PF_DECnet                    = AF_DECnet;
   PF_DLI                       = AF_DLI;
   PF_LAT                       = AF_LAT;
   PF_HYLINK                    = AF_HYLINK;
   PF_APPLETALK                 = AF_APPLETALK;
   PF_NETBIOS                   = AF_NB;
   PF_NB                        = AF_NB;
{$IFDEF WINDOWS}
   PF_VOICEVIEW                 = AF_VOICEVIEW;
{$ELSE}
   PF_OS2                       = AF_OS2;
{$ENDIF}
   PF_MAX                       = AF_MAX;


  FREAD                         = 1;
  FWRITE                        = 2;

  MSG_OOB                       = $1;              (* process out-of-band data *)
  MSG_PEEK                      = $2;              (* peek at incoming message *)
  MSG_DONTROUTE                 = $4;              (* send without using routing tables *)
  MSG_FULLREAD                  = $8;              (* send without using routing tables *)

  MSG_MAXIOVLEN                 = 16;


{$IFDEF OS2}
  FIONREAD                      = Ord('f')*256 or 127;  (* get # bytes to read *)
  FIONBIO                       = Ord('f')*256 or 126;  (* set/clear non-blocking I/O *)
  FIOASYNC                      = Ord('f')*256 or 125;  (* set/clear async I/O *)
  FIOTCPCKSUM                   = Ord('f')*256 or 128;
  FIONSTATUS                    = Ord('f')*256 or 120;
  FIONURG                       = Ord('f')*256 or 121;
  FIOBSTATUS                    = Ord('f')*256 or 122;

  SIOCSHIWAT                    = Ord('s')*256 or  0;   (* set high watermark *)
  SIOCGHIWAT                    = Ord('s')*256 or  1;   (* get high watermark *)
  SIOCSLOWAT                    = Ord('s')*256 or  2;   (* set low watermark *)
  SIOCGLOWAT                    = Ord('s')*256 or  3;   (* get low watermark *)
  SIOCATMARK                    = Ord('s')*256 or  7;   (* at oob mark? *)
  SIOCSPGRP                     = Ord('s')*256 or  8;
  SIOCGPGRP                     = Ord('s')*256 or  9;
  SIOCSHOSTID                   = Ord('s')*256 or 10;

(* NEW IOCTL COMMAND CODES FOR AFNB                                   *)
(* SIOCGNCBFN  - Issue NETBIOS NCB.FIND.NAME                          *)
(* SIOCGNBNAME - Get NETBIOS HOSTNAME                                 *)
(* SIOCSNBNAME - Set NETBIOS HOSTNAME                                 *)

  SIOCGNBNAME                   = Ord('s')*256 or 11;
  SIOCSNBNAME                   = Ord('s')*256 or 12;
  SIOCGNCBFN                    = Ord('s')*256 or 13;

  SIOCADDRT                     = Ord('r')*256 or 10;
  SIOCDELRT                     = Ord('r')*256 or 11;
  SIOMETRIC1RT                  = Ord('r')*256 or 12;
  SIOMETRIC2RT                  = Ord('r')*256 or 13;
  SIOMETRIC3RT                  = Ord('r')*256 or 14;
  SIOMETRIC4RT                  = Ord('r')*256 or 15;

  SIOCREGADDNET                 = Ord('r')*256 or 12;
  SIOCREGDELNET                 = Ord('r')*256 or 13;
  SIOCREGROUTES                 = Ord('r')*256 or 14;
  SIOCFLUSHROUTES               = Ord('r')*256 or 15;

  SIOCSIFADDR                   = Ord('i')*256 or 12;
  SIOCGIFADDR                   = Ord('i')*256 or 13;
  SIOCSIFDSTADDR                = Ord('i')*256 or 14;
  SIOCGIFDSTADDR                = Ord('i')*256 or 15;
  SIOCSIFFLAGS                  = Ord('i')*256 or 16;
  SIOCGIFFLAGS                  = Ord('i')*256 or 17;
  SIOCGIFBRDADDR                = Ord('i')*256 or 18;
  SIOCSIFBRDADDR                = Ord('i')*256 or 19;
  SIOCGIFCONF                   = Ord('i')*256 or 20;
  SIOCGIFNETMASK                = Ord('i')*256 or 21;
  SIOCSIFNETMASK                = Ord('i')*256 or 22;
  SIOCGIFMETRIC                 = Ord('i')*256 or 23;
  SIOCSIFMETRIC                 = Ord('i')*256 or 24;
  SIOCSIFSETSIG                 = Ord('i')*256 or 25;
  SIOCSIFCLRSIG                 = Ord('i')*256 or 26;
  SIOCSIFBRD                    = Ord('i')*256 or 27; (* SINGLE-rt bcst. using old # for bkw cmpt *)
  SIOCSIFALLRTB                 = Ord('i')*256 or 63; (* added to configure all-route broadcst *)

  SIOCGIFLOAD                   = Ord('i')*256 or 27;
  SIOCSIFFILTERSRC              = Ord('i')*256 or 28;
  SIOCGIFFILTERSRC              = Ord('i')*256 or 29;

  SIOCSARP                      = Ord('i')*256 or 30;
  SIOCGARP                      = Ord('i')*256 or 31;
  SIOCDARP                      = Ord('i')*256 or 32;
  SIOCSIFSNMPSIG                = Ord('i')*256 or 33;
  SIOCSIFSNMPCLR                = Ord('i')*256 or 34;
  SIOCSIFSNMPCRC                = Ord('i')*256 or 35;
  SIOCSIFPRIORITY               = Ord('i')*256 or 36;
  SIOCGIFPRIORITY               = Ord('i')*256 or 37;
  SIOCSIFFILTERDST              = Ord('i')*256 or 38;
  SIOCGIFFILTERDST              = Ord('i')*256 or 39;
  SIOCSIF802_3                  = Ord('i')*256 or 40;
  SIOCSIFNO802_3                = Ord('i')*256 or 41;
  SIOCSIFNOREDIR                = Ord('i')*256 or 42;
  SIOCSIFYESREDIR               = Ord('i')*256 or 43;

  SIOCSIFMTU                    = Ord('i')*256 or 45;
  SIOCSIFFDDI                   = Ord('i')*256 or 46;
  SIOCSIFNOFDDI                 = Ord('i')*256 or 47;
  SIOCSRDBRD                    = Ord('i')*256 or 48;
  SIOCSARP_TR                   = Ord('i')*256 or 49;
  SIOCGARP_TR                   = Ord('i')*256 or 50;

(* multicast ioctls *)
  SIOCADDMULTI                  = Ord('i')*256 or 51;    (* add m'cast addr *)
  SIOCDELMULTI                  = Ord('i')*256 or 52;    (* del m'cast addr *)
  SIOCMULTISBC                  = Ord('i')*256 or 61;   (* use broadcast to send IP multicast*)
  SIOCMULTISFA                  = Ord('i')*256 or 62;   (* use functional addr to send IP multicast*)

(* alias *)
  SIOCAIFADDR                   = Ord('i')*256 or 63;   (* add an alias IP address *)
  SIOCDIFADDR                   = Ord('i')*256 or 64;   (* del an alias IP address *)


  SIOCGUNIT                     = Ord('i')*256 or 70;  (* Used to retreive unit number on *)
                                                                      (* serial interface *)

  SIOCSIFSPIPE                  = Ord('i')*256 or 71;   (* used to set pipe size on interface *)
                                                        (* this is used as tcp send buffer size *)
  SIOCSIFRPIPE                  = Ord('i')*256 or 72;   (* used to set pipe size on interface *)
                                                        (* this is used as tcp recv buffer size *)
  SIOCSIFTCPSEG                 = Ord('i')*256 or 73;   (* set the TCP segment size on interface*)
  SIOCSIFUSE576                 = Ord('i')*256 or 74;   (* enable/disable the automatic change of mss to 576 *)
                                                        (* if going through a router *)
  SIOCGIFVALID                  = Ord('i')*256 or 75;   (* to check if the interface is Valid or not *)

  SIOCGIFBOUND                  = Ord('i')*256 or 76;   (* ioctl to return bound/shld bind ifs *)

(* Get multicast gp. info for an interface  *)
  SIOCGMCAST                    = Ord('i')*256 or 81;  (* ret list of m-cast addrs for an if *)

(* Interface Tracing Support *)
  SIOCGIFEFLAGS                 = Ord('i')*256 or 150;
  SIOCSIFEFLAGS                 = Ord('i')*256 or 151;
  SIOCGIFTRACE                  = Ord('i')*256 or 152;
  SIOCSIFTRACE                  = Ord('i')*256 or 153;

  SIOCSSTAT                     = Ord('i')*256 or 154;
  SIOCGSTAT                     = Ord('i')*256 or 155;

(* NETSTAT stuff *)
  SIOSTATMBUF                   = Ord('n')*256 or 40;
  SIOSTATTCP                    = Ord('n')*256 or 41;
  SIOSTATUDP                    = Ord('n')*256 or 42;
  SIOSTATIP                     = Ord('n')*256 or 43;
  SIOSTATSO                     = Ord('n')*256 or 44;
  SIOSTATRT                     = Ord('n')*256 or 45;
  SIOFLUSHRT                    = Ord('n')*256 or 46;
  SIOSTATICMP                   = Ord('n')*256 or 47;
  SIOSTATIF                     = Ord('n')*256 or 48;
  SIOSTATAT                     = Ord('n')*256 or 49;
  SIOSTATARP                    = Ord('n')*256 or 50;
  SIOSTATIF42                   = Ord('n')*256 or 51;
(* ioctls which return the cnt of the arp and route entris *)
  SIOSTATCNTRT                  = Ord('n')*256 or 52;
  SIOSTATCNTAT                  = Ord('n')*256 or 53;
{$ELSE}
(* WIN32 IOCTL COMMANDS *)
  IOCPARM_MASK                  = $7F;          (* parameters must be < 128 bytes *)
  IOC_VOID                      = $20000000;    (* no parameters *)
  IOC_OUT                       = $40000000;    (* copy out parameters *)
  IOC_IN                        = $80000000;    (* copy in parameters *)
  IOC_INOUT                     = IOC_IN or IOC_OUT;
                                                (* 0x20000000 distinguises new and old ioctl's *)
  FIONREAD                      = IOC_OUT or (SizeOf(LongInt) and IOCPARM_MASK)*65536 or Ord('f')*256 or 127;
  FIONBIO                       = IOC_IN  or (SizeOf(LongInt) and IOCPARM_MASK)*65536 or Ord('f')*256 or 126;
  FIOASYNC                      = IOC_IN  or (SizeOf(LongInt) and IOCPARM_MASK)*65536 or Ord('f')*256 or 125;

  SIOCSHIWAT                    = IOC_IN  or (SizeOf(LongInt) and IOCPARM_MASK)*65536 or Ord('s')*256 or 000;
  SIOGSHIWAT                    = IOC_OUT or (SizeOf(LongInt) and IOCPARM_MASK)*65536 or Ord('s')*256 or 001;
  SIOCSLOWAT                    = IOC_IN  or (SizeOf(LongInt) and IOCPARM_MASK)*65536 or Ord('s')*256 or 002;
  SIOGSLOWAT                    = IOC_OUT or (SizeOf(LongInt) and IOCPARM_MASK)*65536 or Ord('s')*256 or 003;
  SIOCATMARK                    = IOC_OUT or (SizeOf(LongInt) and IOCPARM_MASK)*65536 or Ord('s')*256 or 007;
{$ENDIF}

(*
 * Structure used by kernel to store most
 * addresses.
 *)
Type
  sockaddr                      = record
    sa_family                   : UShort;
    sa_data                     : Array[0..13] of Byte;
  end;
(*
 * Structure used by kernel to pass protocol
 * information in raw Sockets.
 *)
  sockproto                     = record
    sp_family                   : UShort;
    sp_protocol                 : UShort;
  end;

  iovec                         = record
    iov_base                    : PChar;
    iov_len                     : Integer;
  end;

(*
 * Message header for recvmsg and sendmsg calls.
 *)
  msghdr                        = record
    msg_name                    : PChar;
    msg_namelen                 : Integer;
    msg_iov                     : ^ioVec;
    msg_iovlen                  : Integer;
    msg_accrights               : PChar;
    msg_accrightslen            : Integer;
  end;

  uio                           = record
    uio_iov                     : ^ioVec;
    uio_iovcnt                  : Integer;
    uio_offset                  : Longint;
    uio_segflg                  : Integer;
    uio_resid                   : Integer;
  end;

  uio_rw                        = (UIO_READ, UIO_WRITE);

  hostent                       = record
    h_name                      : PChar;        (* official name of host *)
    h_aliases                   :^PChar;        (* alias list *)
    h_addrtype                  : Integer;      (* host address type *)
    h_length                    : Integer;      (* length of address *)
    h_addr                      :^PChar;        (* list of addresses from name server *)
  end;

  netent                        = record
    n_name                      : PChar;        (* official name of net *)
    n_aliases                   :^PChar;        (* alias list *)
    n_addrtype                  : Integer;      (* net address type *)
    n_net                       : LongInt;      (* network # *)
  end;

  servent                       = record
    s_name                      : PChar;        (* official service name *)
    s_aliases                   :^PChar;        (* alias list *)
    s_port                      : Integer;      (* port # *)
    s_proto                     : PChar;        (* protocol to use *)
  end;

  protoent                      = record
    p_name                      : PChar;        (* official protocol name *)
    p_aliases                   :^PChar;        (* alias list *)
    p_proto                     : Integer;      (* protocol # *)
  end;

(*
 * After a successful call to gethostbyname_r()/gethostbyaddr_r(), the
 * structure hostent_data will contain the data to which pointers in
 * the hostent structure will point to.
 *)
  hostent_data                  = record
    host_addr                   : in_addr;      (* host address pointer *)
    h_addr_ptrs                 : Array[0.._MAX_ADDRS] of PChar; (* host address *)
    hostaddr                    : Array[0.._MAX_ADDRS-1] of Char;
    hostbuf                     : Array[0.._HOSTBUFSIZE] of Char; (* host data *)
    host_aliases                : Array[0.._MAX_ALIASES-1] of PChar;
    host_addrs                  : Array[0..1] of PChar;
    hostf                       : Pointer;
    stayopen                    : Integer;      (* AIX addon *)
    host_addresses              : Array[0.._MAX_ADDRS-1] of LongInt; (* As per defect 48367. *)
  end;

  servent_data                  = record        (* should be considered opaque *)
    serv_fp                     : Pointer;
    line                        : Array[0.._MAXLINELEN-1] of Char;
    serv_aliases                : Array[0.._MAX_ALIASES-1] of PChar;
    _serv_stayopen              : Integer;
  end;

  (* WinSock Compatibility & useful *)
  PSOCKADDR                     =^SOCKADDR;
  LPSOCKADDR                    = PSOCKADDR;
  PSOCKADDR_IN                  =^SOCKADDR_IN;
  LPSOCKADDR_IN                 = PSOCKADDR_IN;
  PLINGER                       =^LINGER;
  LPLINGER                      = PLINGER;
  PIN_ADDR                      =^IN_ADDR;
  LPIN_ADDR                     = PIN_ADDR;
  PHOSTENT                      =^HOSTENT;
  LPHOSTENT                     = PHOSTENT;
  PNETENT                       =^NETENT;
  LPNETENT                      = PNETENT;
  PSERVENT                      =^SERVENT;
  LPSERVENT                     = PSERVENT;
  PPROTOENT                     =^PROTOENT;
  LPPROTOENT                    = PPROTOENT;


// I'll have to sort this out properly sometime...

//  PFD_Set               =^TFD_Set;
//  TFD_Set               = Array[0..255] of Byte;
{  TFD_Set                 = record
    TFD_Size              : Integer;
    TFD_Last              : Integer;
    TFD_Sockets           :^TSocket;
  end;

Procedure FD_Zero(var fd:TFD_Set);inline;
begin
  if fd

Procedure FD_Zero(var fd:TFD_Set);inline;
begin FillChar(fd,sizeof(fd),0); end;
Procedure FD_Set(Sock:TSocket;var fd:TFD_Set);inline;
begin fd[Sock div 8]:=fd[Sock div 8] or (1 shl (Sock mod 8)); end;
Function FD_IsSet(Sock:TSocket;var fd:TFD_Set):Boolean;inline;
begin FD_IsSet:=(fd[Sock div 8] and (1 shl (Sock mod 8)))<>0; end;}


function socket(af,typ,proto:Integer):Integer;
function listen(s:Integer;backlog:Integer):Integer;
function accept(s:Integer;var addr;var size:Integer):Integer;
function bind(s:Integer;var addr; size:Integer):Integer;
function connect(s:Integer;var addr; size:Integer):Integer;
function getpeername(s:Integer;var addr; var size:Integer):Integer;
function getsockname(s:Integer;var addr; var size:Integer):Integer;
function getsockopt(s:Integer;level,optname:Word;var optval;var optlen:Integer):Integer;
function setsockopt(s:Integer;level,optname:Word;var optval;optlen:Integer):Integer;

function recv(s:Integer;var buf; len,flags:Integer):Integer;
function recvfrom(s:Integer;var buf; len,flags:Integer; var from; var fromlen:Integer):Integer;

function send(s:Integer;var buf; len,flags:Integer):Integer;
function sendto(s:Integer;var buf; len,flags:Integer; var dest; var destlen:Integer):Integer;

function shutdown(s:Integer;how:Integer):Integer;

function soclose(s:Integer):Integer;
function soabort(s:Integer):Integer;
function socancel(s:Integer):Integer;
function soioctl(s:Integer;cmd:LongInt;var argp; argsize:Integer):Integer;

function inet_addr(cp:PChar):ULONG;
function inet_ntoa(ia:{in_addr}ULONG):PChar;

function sock_errno:Integer;
function sock_errstr(dest:PChar):PChar;
function set_errno(errno:Integer):Integer;

function htonl(l:ULONG):ULONG;
function ntohl(l:ULONG):ULONG;
function htons(s:USHORT):USHORT;
function ntohs(s:USHORT):USHORT;

function sock_init:Integer;
function sock_done:Integer;
function getinetversion:PChar;

function gethostbyname_r(name:PChar;var ent:hostent;var data:hostent_data):Integer;
function gethostbyaddr_r(var addr;addrlen,addrfam:Integer;var ent:hostent;var data:hostent_data):Integer;
function getservbyname_r(name,proto:PChar;var ent:servent;var data:servent_data):Integer;
function gethostname(name:PChar;namelen:Integer):Integer;
function gethostbyname(name:PChar):PHOSTENT;
function gethostbyaddr(var addr;addrlen,addrfam:Integer):PHOSTENT;
function getnetbyname(name:PChar):PNETENT;
function getnetbyaddr(net:LongInt;nettype:Integer):PNETENT;
function getservbyname(name,proto:PChar):PSERVENT;
function getservbyport(port:Integer;proto:PChar):PSERVENT;
function getprotobyname(proto:PChar):PPROTOENT;
function getprotobynumber(proto:Integer):PPROTOENT;
{function getprotobyport}

procedure sethostent(idx:Integer);
function  gethostent:PHOSTENT;
procedure endhostent;
procedure setnetent(idx:Integer);
function  getnetent:PNETENT;
procedure endnetent;
procedure setprotoent(idx:Integer);
function  getprotoent:PPROTOENT;
procedure endprotoent;
procedure setservent(idx:Integer);
function  getservent:PSERVENT;
procedure endservent;
{&CDecl-}

const

{$IFDEF OS2}
  SOCBASEERR            = 10000;

(*
 * OS/2 SOCKET API definitions of regular Microsoft C 6.0 error constants
 *)

  SOCEPERM              = (SOCBASEERR+1);            (* Not owner *)
  SOCESRCH              = (SOCBASEERR+3);            (* No such process *)
  SOCEINTR              = (SOCBASEERR+4);            (* Interrupted system call *)
  SOCENXIO              = (SOCBASEERR+6);            (* No such device or address *)
  SOCEBADF              = (SOCBASEERR+9);            (* Bad file number *)
  SOCEACCES             = (SOCBASEERR+13);           (* Permission denied *)
  SOCEFAULT             = (SOCBASEERR+14);           (* Bad address *)
  SOCEINVAL             = (SOCBASEERR+22);           (* Invalid argument *)
  SOCEMFILE             = (SOCBASEERR+24);           (* Too many open files *)
  SOCEPIPE              = (SOCBASEERR+32);           (* Broken pipe *)

  SOCEOS2ERR            = (SOCBASEERR+100);           (* OS/2 Error *)

(*
 * OS/2 SOCKET API definitions of regular BSD error constants
 *)

  SOCEWOULDBLOCK        = (SOCBASEERR+35);           (* Operation would block *)
  SOCEINPROGRESS        = (SOCBASEERR+36);           (* Operation now in progress *)
  SOCEALREADY           = (SOCBASEERR+37);           (* Operation already in progress *)
  SOCENOTSOCK           = (SOCBASEERR+38);           (* Socket operation on non-socket *)
  SOCEDESTADDRREQ       = (SOCBASEERR+39);           (* Destination address required *)
  SOCEMSGSIZE           = (SOCBASEERR+40);           (* Message too long *)
  SOCEPROTOTYPE         = (SOCBASEERR+41);           (* Protocol wrong type for socket *)
  SOCENOPROTOOPT        = (SOCBASEERR+42);           (* Protocol not available *)
  SOCEPROTONOSUPPORT    = (SOCBASEERR+43);           (* Protocol not supported *)
  SOCESOCKTNOSUPPORT    = (SOCBASEERR+44);           (* Socket type not supported *)
  SOCEOPNOTSUPP         = (SOCBASEERR+45);           (* Operation not supported on socket *)
  SOCEPFNOSUPPORT       = (SOCBASEERR+46);           (* Protocol family not supported *)
  SOCEAFNOSUPPORT       = (SOCBASEERR+47);           (* Address family not supported by protocol family *)
  SOCEADDRINUSE         = (SOCBASEERR+48);           (* Address already in use *)
  SOCEADDRNOTAVAIL      = (SOCBASEERR+49);           (* Can't assign requested address *)
  SOCENETDOWN           = (SOCBASEERR+50);           (* Network is down *)
  SOCENETUNREACH        = (SOCBASEERR+51);           (* Network is unreachable *)
  SOCENETRESET          = (SOCBASEERR+52);           (* Network dropped connection on reset *)
  SOCECONNABORTED       = (SOCBASEERR+53);           (* Software caused connection abort *)
  SOCECONNRESET         = (SOCBASEERR+54);           (* Connection reset by peer *)
  SOCENOBUFS            = (SOCBASEERR+55);           (* No buffer space available *)
  SOCEISCONN            = (SOCBASEERR+56);           (* Socket is already connected *)
  SOCENOTCONN           = (SOCBASEERR+57);           (* Socket is not connected *)
  SOCESHUTDOWN          = (SOCBASEERR+58);           (* Can't send after socket shutdown *)
  SOCETOOMANYREFS       = (SOCBASEERR+59);           (* Too many references: can't splice *)
  SOCETIMEDOUT          = (SOCBASEERR+60);           (* Connection timed out *)
  SOCECONNREFUSED       = (SOCBASEERR+61);           (* Connection refused *)
  SOCELOOP              = (SOCBASEERR+62);           (* Too many levels of symbolic links *)
  SOCENAMETOOLONG       = (SOCBASEERR+63);           (* File name too long *)
  SOCEHOSTDOWN          = (SOCBASEERR+64);           (* Host is down *)
  SOCEHOSTUNREACH       = (SOCBASEERR+65);           (* No route to host *)
  SOCENOTEMPTY          = (SOCBASEERR+66);           (* Directory not empty *)

(*
 * OS/2 SOCKET API errors redefined as regular BSD error constants
 *)

  EWOULDBLOCK           = SOCEWOULDBLOCK;
  EINPROGRESS           = SOCEINPROGRESS;
  EALREADY              = SOCEALREADY;
  ENOTSOCK              = SOCENOTSOCK;
  EDESTADDRREQ          = SOCEDESTADDRREQ;
  EMSGSIZE              = SOCEMSGSIZE;
  EPROTOTYPE            = SOCEPROTOTYPE;
  ENOPROTOOPT           = SOCENOPROTOOPT;
  EPROTONOSUPPORT       = SOCEPROTONOSUPPORT;
  ESOCKTNOSUPPORT       = SOCESOCKTNOSUPPORT;
  EOPNOTSUPP            = SOCEOPNOTSUPP;
  EPFNOSUPPORT          = SOCEPFNOSUPPORT;
  EAFNOSUPPORT          = SOCEAFNOSUPPORT;
  EADDRINUSE            = SOCEADDRINUSE;
  EADDRNOTAVAIL         = SOCEADDRNOTAVAIL;
  ENETDOWN              = SOCENETDOWN;
  ENETUNREACH           = SOCENETUNREACH;
  ENETRESET             = SOCENETRESET;
  ECONNABORTED          = SOCECONNABORTED;
  ECONNRESET            = SOCECONNRESET;
  ENOBUFS               = SOCENOBUFS;
  EISCONN               = SOCEISCONN;
  ENOTCONN              = SOCENOTCONN;
  ESHUTDOWN             = SOCESHUTDOWN;
  ETOOMANYREFS          = SOCETOOMANYREFS;
  ETIMEDOUT             = SOCETIMEDOUT;
  ECONNREFUSED          = SOCECONNREFUSED;
  ELOOP                 = SOCELOOP;
  ENAMETOOLONG          = SOCENAMETOOLONG;
  EHOSTDOWN             = SOCEHOSTDOWN;
  EHOSTUNREACH          = SOCEHOSTUNREACH;
  ENOTEMPTY             = SOCENOTEMPTY;
{$ELSE}
(*
 * All Windows Sockets error constants are biased by WSABASEERR from
 * the "normal"
 *)
  WSABASEERR            = 10000;
(*
 * Windows Sockets definitions of regular Microsoft C error constants
 *)
  WSAEINTR              = (WSABASEERR+4);
  WSAEBADF              = (WSABASEERR+9);
  WSAEACCES             = (WSABASEERR+13);
  WSAEFAULT             = (WSABASEERR+14);
  WSAEINVAL             = (WSABASEERR+22);
  WSAEMFILE             = (WSABASEERR+24);

(*
 * Windows Sockets definitions of regular Berkeley error constants
 *)
  WSAEWOULDBLOCK        = (WSABASEERR+35);
  WSAEINPROGRESS        = (WSABASEERR+36);
  WSAEALREADY           = (WSABASEERR+37);
  WSAENOTSOCK           = (WSABASEERR+38);
  WSAEDESTADDRREQ       = (WSABASEERR+39);
  WSAEMSGSIZE           = (WSABASEERR+40);
  WSAEPROTOTYPE         = (WSABASEERR+41);
  WSAENOPROTOOPT        = (WSABASEERR+42);
  WSAEPROTONOSUPPORT    = (WSABASEERR+43);
  WSAESOCKTNOSUPPORT    = (WSABASEERR+44);
  WSAEOPNOTSUPP         = (WSABASEERR+45);
  WSAEPFNOSUPPORT       = (WSABASEERR+46);
  WSAEAFNOSUPPORT       = (WSABASEERR+47);
  WSAEADDRINUSE         = (WSABASEERR+48);
  WSAEADDRNOTAVAIL      = (WSABASEERR+49);
  WSAENETDOWN           = (WSABASEERR+50);
  WSAENETUNREACH        = (WSABASEERR+51);
  WSAENETRESET          = (WSABASEERR+52);
  WSAECONNABORTED       = (WSABASEERR+53);
  WSAECONNRESET         = (WSABASEERR+54);
  WSAENOBUFS            = (WSABASEERR+55);
  WSAEISCONN            = (WSABASEERR+56);
  WSAENOTCONN           = (WSABASEERR+57);
  WSAESHUTDOWN          = (WSABASEERR+58);
  WSAETOOMANYREFS       = (WSABASEERR+59);
  WSAETIMEDOUT          = (WSABASEERR+60);
  WSAECONNREFUSED       = (WSABASEERR+61);
  WSAELOOP              = (WSABASEERR+62);
  WSAENAMETOOLONG       = (WSABASEERR+63);
  WSAEHOSTDOWN          = (WSABASEERR+64);
  WSAEHOSTUNREACH       = (WSABASEERR+65);
  WSAENOTEMPTY          = (WSABASEERR+66);
  WSAEPROCLIM           = (WSABASEERR+67);
  WSAEUSERS             = (WSABASEERR+68);
  WSAEDQUOT             = (WSABASEERR+69);
  WSAESTALE             = (WSABASEERR+70);
  WSAEREMOTE            = (WSABASEERR+71);

  WSAEDISCON            = (WSABASEERR+101);

(*
 * Extended Windows Sockets error constant definitions
 *)
  WSASYSNOTREADY        = (WSABASEERR+91);
  WSAVERNOTSUPPORTED    = (WSABASEERR+92);
  WSANOTINITIALISED     = (WSABASEERR+93);

(*
 * Resolver error codes
 *)
  WSAHOST_NOT_FOUND     = (WSABASEERR+1001);
  WSATRY_AGAIN          = (WSABASEERR+1002);
  WSANO_RECOVERY        = (WSABASEERR+1003);
  WSANO_DATA            = (WSABASEERR+1004);
  WSANO_ADDRESS         = WSANO_DATA;

(*
 * WinSock SOCKET API errors redefined as regular BSD error constants
 *)

  EWOULDBLOCK           = WSAEWOULDBLOCK;
  EINPROGRESS           = WSAEINPROGRESS;
  EALREADY              = WSAEALREADY;
  ENOTSOCK              = WSAENOTSOCK;
  EDESTADDRREQ          = WSAEDESTADDRREQ;
  EMSGSIZE              = WSAEMSGSIZE;
  EPROTOTYPE            = WSAEPROTOTYPE;
  ENOPROTOOPT           = WSAENOPROTOOPT;
  EPROTONOSUPPORT       = WSAEPROTONOSUPPORT;
  ESOCKTNOSUPPORT       = WSAESOCKTNOSUPPORT;
  EOPNOTSUPP            = WSAEOPNOTSUPP;
  EPFNOSUPPORT          = WSAEPFNOSUPPORT;
  EAFNOSUPPORT          = WSAEAFNOSUPPORT;
  EADDRINUSE            = WSAEADDRINUSE;
  EADDRNOTAVAIL         = WSAEADDRNOTAVAIL;
  ENETDOWN              = WSAENETDOWN;
  ENETUNREACH           = WSAENETUNREACH;
  ENETRESET             = WSAENETRESET;
  ECONNABORTED          = WSAECONNABORTED;
  ECONNRESET            = WSAECONNRESET;
  ENOBUFS               = WSAENOBUFS;
  EISCONN               = WSAEISCONN;
  ENOTCONN              = WSAENOTCONN;
  ESHUTDOWN             = WSAESHUTDOWN;
  ETOOMANYREFS          = WSAETOOMANYREFS;
  ETIMEDOUT             = WSAETIMEDOUT;
  ECONNREFUSED          = WSAECONNREFUSED;
  ELOOP                 = WSAELOOP;
  ENAMETOOLONG          = WSAENAMETOOLONG;
  EHOSTDOWN             = WSAEHOSTDOWN;
  EHOSTUNREACH          = WSAEHOSTUNREACH;
  ENOTEMPTY             = WSAENOTEMPTY;
{$ENDIF}


implementation
uses Strings;

function not_impl:Integer; inline; begin set_errno(10045); Result := -1 end;

const
  sockets       = {$IFDEF OS2}'SO32DLL'{$ELSE}'WSOCK32'{$ENDIF};
  network       = {$IFDEF OS2}'TCP32DLL'{$ELSE}'WSOCK32'{$ENDIF};

function socket;          external sockets index {$IFDEF OS2}16{$ELSE} 23{$ENDIF};
function listen;          external sockets index {$IFDEF OS2} 9{$ELSE} 13{$ENDIF};
function accept;          external sockets index 1;
function bind;            external sockets index 2;
function connect;         external sockets index {$IFDEF OS2} 3{$ELSE}  4{$ENDIF};
function getpeername;     external sockets index 5;
function getsockname;     external sockets index 6;
function getsockopt;      external sockets index 7;
function setsockopt;      external sockets index {$IFDEF OS2}15{$ELSE} 21{$ENDIF};

function recv;            external sockets index {$IFDEF OS2}10{$ELSE} 16{$ENDIF};
function recvfrom;        external sockets index {$IFDEF OS2}11{$ELSE} 17{$ENDIF};

function send;            external sockets index {$IFDEF OS2}13{$ELSE} 19{$ENDIF};
function sendto;          external sockets index {$IFDEF OS2}14{$ELSE} 20{$ENDIF};

function shutdown;        external sockets index {$IFDEF OS2}25{$ELSE} 22{$ENDIF};

function soclose;         external sockets index {$IFDEF OS2}17{$ELSE}  3{$ENDIF};
function soioctl;         external sockets index {$IFDEF OS2} 8{$ELSE} 12{$ENDIF};

function inet_addr;       external network index {$IFDEF OS2} 5{$ELSE} 10{$ENDIF};
function inet_ntoa;       external network index {$IFDEF OS2}10{$ELSE} 11{$ENDIF};

function sock_errno;      external sockets index {$IFDEF OS2}20{$ELSE}111{$ENDIF};
function set_errno;       external sockets index {$IFDEF OS2}35{$ELSE}112{$ENDIF};

function htonl;           external network index {$IFDEF OS2} 3{$ELSE}  8{$ENDIF};
function ntohl;           external network index {$IFDEF OS2} 3{$ELSE} 14{$ENDIF};
function htons;           external network index {$IFDEF OS2} 4{$ELSE}  9{$ENDIF};
function ntohs;           external network index {$IFDEF OS2} 4{$ELSE} 15{$ENDIF};

function gethostname;     external network index {$IFDEF OS2}44{$ELSE}57{$ENDIF};
function gethostbyname;   external network index {$IFDEF OS2}11{$ELSE}52{$ENDIF};
function gethostbyaddr;   external network index {$IFDEF OS2}12{$ELSE}51{$ENDIF};
function getservbyname;   external network index {$IFDEF OS2}24{$ELSE}55{$ENDIF};
function getservbyport;   external network index {$IFDEF OS2}23{$ELSE}56{$ENDIF};
function getprotobyname;  external network index {$IFDEF OS2}21{$ELSE}53{$ENDIF};
function getprotobynumber;external network index {$IFDEF OS2}22{$ELSE}54{$ENDIF};

{$IFDEF OS2}
const
  sockver               : Array[0..127] of Char = 'unknown stack';
function _getinetversion(buff:PChar):Integer; CDecl; external sockets index 31;
function getinetversion;
begin
  Result := PChar(@sockver[0]);
  _getinetversion(Result);
end;
function sock_init; external sockets index 26;
function soabort;         external sockets index 19;
function socancel;        external sockets index 18;
function sock_done;       begin Result := 0 end;
function gethostbyname_r; external network index 48;
function gethostbyaddr_r; external network index 49;
function getservbyname_r; external network index 50;
function getnetbyname;    external network index 13;
function getnetbyaddr;    external network index 14;
procedure sethostent;     external network index 28;
function  gethostent;     external network index 30;
procedure endhostent;     external network index 29;
procedure setnetent;      external network index 15;
function  getnetent;      external network index 17;
procedure endnetent;      external network index 16;
procedure setprotoent;    external network index 18;
function  getprotoent;    external network index 20;
procedure endprotoent;    external network index 19;
procedure setservent;     external network index 25;
function  getservent;     external network index 27;
procedure endservent;     external network index 26;
{$ELSE}
const
  versionreq            = $0101;
  WSADESCRIPTION_LEN    = 256;
  WSASYS_STATUS_LEN     = 128;
  wsaData               : record
    wVersion            : USHORT;
    wHighVersion        : USHORT;
    szDescription       : Array[0..WSADESCRIPTION_LEN] of Char;
    szSystemStatus      : Array[0..WSASYS_STATUS_LEN] of Char;
    iMaxSoxkets         : USHORT;
    iMaxUdpDg           : USHORT;
    lpVendorInfo        : Pointer;
  end = (wVersion:0;wHighVersion:0;szDescription:'unknown stack');
function sock_done;       external sockets index 116;
function soabort;         begin Result := not_impl end;
function socancel;        begin Result := not_impl end;
function gethostbyname_r; begin Result := not_impl end;
function gethostbyaddr_r; begin Result := not_impl end;
function getservbyname_r; begin Result := not_impl end;
function getnetbyname;    begin not_impl; Result := nil end;
function getnetbyaddr;    begin not_impl; Result := nil end;
procedure sethostent;     begin not_impl end;
function  gethostent;     begin not_impl; Result := nil end;
procedure endhostent;     begin end;
procedure setnetent;      begin not_impl end;
function  getnetent;      begin not_impl; Result := nil end;
procedure endnetent;      begin end;
procedure setprotoent;    begin not_impl end;
function  getprotoent;    begin not_impl; Result := nil end;
procedure endprotoent;    begin end;
procedure setservent;     begin not_impl end;
function  getservent;     begin not_impl; Result := nil end;
procedure endservent;     begin end;
function getinetversion;  begin Result := PChar(@wsaData.szDescription[0]) end;
function WSAStartup(ver:WORD;var lpWSAData):Integer; stdcall; external sockets index 115;

function sock_init:Integer;
begin
  if WSAStartUp(versionreq,wsaData)<>0 then begin
    sock_init := -1;
    exit;
  end;
  if (Lo(wsaData.wVersion)<>1) or (Hi(wsaData.wVersion)<>1) then begin
    sock_done;
    sock_init := -1;
    exit;
  end;
  sock_init := 0;
end;
{$ENDIF}

const
  ErrorStrings          : Array[0..41] of record
    err                 : Integer;
    str                 : PChar;
  end = (
      (err:10001; str:'not owner'),
      (err:10003; str:'no such process'),
      (err:10004; str:'interrupted system call'),
      (err:10006; str:'no such device or address'),
      (err:10009; str:'bad file number'),
      (err:10013; str:'permission denied'),
      (err:10014; str:'bad address'),
      (err:10022; str:'invalid argument'),
      (err:10024; str:'too many open files'),
      (err:10032; str:'broken pipe'),
      (err:10035; str:'operation would block'),
      (err:10036; str:'operation now in progress'),
      (err:10037; str:'operation already in progress'),
      (err:10038; str:'socket operation on non-socket'),
      (err:10039; str:'destination address required'),
      (err:10040; str:'message too long'),
      (err:10041; str:'protocol wrong type for socket'),
      (err:10042; str:'protocol not available'),
      (err:10043; str:'protocol not supported'),
      (err:10044; str:'socket type not supported'),
      (err:10045; str:'operation not supported on socket'),
      (err:10046; str:'protocol family not supported'),
      (err:10047; str:'address family not supported by protocol family'),
      (err:10048; str:'address is already in use'),
      (err:10049; str:'can''t assign requested address'),
      (err:10050; str:'network is down'),
      (err:10051; str:'network is unreachable'),
      (err:10052; str:'network dropped connection on reset'),
      (err:10053; str:'software caused connection abort'),
      (err:10054; str:'connection reset by peer'),
      (err:10055; str:'no buffer space available'),
      (err:10056; str:'socket is already connected'),
      (err:10057; str:'socket is not connected'),
      (err:10058; str:'can''t send after socket shutdown'),
      (err:10059; str:'too many references: can''t splice'),
      (err:10060; str:'connection timed out'),
      (err:10061; str:'connection refused'),
      (err:10062; str:'too many levels of symbolic links'),
      (err:10063; str:'file name too long'),
      (err:10064; str:'host is down'),
      (err:10065; str:'no route to host'),
      (err:10066; str:'directory not empty')
  );

function sock_errstr(dest:PChar):PChar;
var
  err           : Integer;
  i,j,k         : Integer;
begin
  err := sock_errno;
  j := Low(ErrorStrings);
  k := High(ErrorStrings);
  repeat;
    i := (j+k+1) div 2;
    if ErrorStrings[i].err>err then k := i-1 else
    if ErrorStrings[i].err<err then j := i+1 else begin
      StrCopy(dest,ErrorStrings[i].str);
      Result := dest;
      exit;
    end;
  until j>k;
  Result := nil;
end;

end.
