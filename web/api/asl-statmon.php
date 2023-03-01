<?php

$r = new ZMQSocket(new ZMQContext(), ZMQ::SOCKET_SUB);
$r->connect ("tcp://127.0.0.1:6750");
$r->setSockOpt(ZMQ::SOCKOPT_SUBSCRIBE, "");
$r->setSockOpt(ZMQ::SOCKOPT_SNDTIMEO, 2000);
$r->setSockOpt(ZMQ::SOCKOPT_RCVTIMEO, 2000);
$r->setSockOpt(ZMQ::SOCKOPT_LINGER, 2000);
$main_loop = 1;
$record = "";
$have_sor = 0;
$eventctr = 0;
$msg = $r->recv();
$r->disconnect("tcp://127.0.0.1:6750");
print($msg);
?>
