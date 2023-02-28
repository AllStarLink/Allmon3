<?php

$r = new ZMQSocket(new ZMQContext(), ZMQ::SOCKET_SUB);
$r->connect ("tcp://127.0.0.1:5555");
$r->setSockOpt(ZMQ::SOCKOPT_SUBSCRIBE, "");

$main_loop = 1;
$record = "";
$have_sor = 0;
$eventctr = 0;
$msg = $r->recv();
print($msg);
?>
