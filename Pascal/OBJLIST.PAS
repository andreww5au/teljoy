unit ObjList;

{   Module: Objlist.pas

    This modules contains the data structure, procedures and functions used
    by the scheduler in manipulating the object records.

}
{$N+,E+}
interface

uses Globals;

type
      list = ^Objectnode;
      Objectnode = record
                 Objct:ObjectRec;
                 tail:list;
                 end;
     AlphaArray = ARRAY [1..7] OF double;

Procedure Error(s:string80);

Function null(l:list):boolean;

Function cons(Obj:ObjectRec; l:list):list;

Procedure head(var Obj:ObjectRec; l:list);

Function tail(l:list):list;

Function consl(l1,l2:list):list;

Function append(l:list; var Obj:ObjectRec):list;

Procedure NewList(var l1:list; Obj:ObjectRec; l2:list);

Function Insert(l:list; Obj:ObjectRec):list;

Function Length(l:list):integer;

Function Copy(l:list):list;

Function Reverse(l:list):list;

Function Reverse1(a,l:list):list;

Procedure CleanUp(l:list);

implementation

procedure Error(s:string80);
  begin
    writeln(s);
    halt;
  end;

function null(l:list):BOOLEAN;
  begin
    if l = nil then
      null:=true
    else
      null:=false;
  end;

function cons(Obj:ObjectRec; l:list):list;
  var NList:list;
  begin
    new(NList);
    NList^.Objct:=Obj;
    NList^.tail:=l;
    cons:=NList;
  end;

procedure head(VAR Obj:ObjectRec; l:list);
  begin
    if null(l) then
      Error('Head(nil)')
    else
      Obj:=l^.Objct;
  end;

function tail(l:list):list;
  begin
    if null(l) then
      begin
        Error('Tail(nil)');
        tail:=nil;
        end
    else
      tail:=l^.tail;
  end;

function consl(l1,l2:list):list;
  var conlist:list;
      NObj:ObjectRec;
  begin
    conlist:=nil;
    new(conlist);
    while not null(l1) do
      begin
        head(NObj,l1);
        conlist:=cons(NObj,conlist);
        l1:=tail(l1);
        end;
    while not null(l2) do
      begin
        head(NObj,l2);
        conlist:=cons(NObj,conlist);
        l2:=tail(l2);
        end;
    consl:=conlist;
  end;

function append(l:list;var Obj:ObjectRec):list;
  var rest:list;
  begin
      if l<>nil then
         begin
              rest:=l;
              while rest^.tail<>nil do   {NOTE- fixed- now returns original }
                    rest:=tail(rest);    {      list, not new list.         }

              rest^.tail:=cons(Obj,nil);
              append:=l;
         end
      else
          append:=cons(Obj,nil);
  end;


procedure NewList(var l1:list; Obj:ObjectRec; l2:list);
  var NList:list;
  begin
    new(NList);
    Nlist^.Objct:=Obj;
    NList^.tail:=l2;
    l1:=Nlist;
  end;

function insert(l:list; Obj:ObjectRec):list;

  procedure InsertAtHead(var qu:list);
    var MinObj:ObjectRec;
    begin
      if not null(qu) then
        begin
          head(MinObj,qu);
          if (Obj.Ra <= MinObj.Ra) then
            if (Obj.Dec <= MinObj.Dec) then
              NewList(qu,Obj,qu)
            else
              InsertAtHead(qu^.tail)
          else
            InsertAtHead(qu^.tail);
        end
      else
        qu:=cons(Obj,qu);
    end; {of procedure InsertAtHead}
  begin
    InsertAtHead(l);
    insert:=l;
  end;

function length(l:list):integer;
  begin
    if null(l) then
      length:=0
    else
      length:=1+length(tail(l));
  end;

function copy(l:list):list;
  var NObj:ObjectRec;
  begin
    if null(l) then
      copy:=nil
    else
      begin
        head(NObj,l);
        copy:=cons(NObj,copy(tail(l)));
        end;
  end;

function reverse(l:list):list;
  var NObj:ObjectRec;
  begin
    if null(l) then
      reverse:=nil
    else
      begin
        head(NObj,l);
        reverse:=append(reverse(tail(l)),NObj);
        end;
  end;

function reverse1(a,l:list):list;
  var NObj:ObjectRec;
  begin
    if null(l) then
      reverse1:=a
    else
      begin
        head(NObj,l);
        reverse1:=reverse1(cons(NObj,a),tail(l));
        end;
  end;

procedure CleanUp(l:list);
  begin
    if not null(l) then
      begin
        CleanUp(tail(l));
        dispose(l);
        end;
  end;

end.
