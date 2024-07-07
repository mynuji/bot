#!/bin/bash


for i in {1..20}
do
	RESULT=$(bluetoothctl connect 34:88:5D:E7:A7:C1)
	echo "$RESULT"
	sleep 2
done
#IFS=$'\n'
#vArray=($RESULT)
#IFS=$''
#
#for vItem in "${vArray[@]}"
#do
#	arr=($vItem)
#
#
#	str=${arr[0]}
#	trimed_str=$( echo $str | sed -e 's/^ *//g' -e 's/ *$//g')
#	echo '[' $trimed_str ']'
#
#
#
#
#
#
##	if [ (${arr[0]} | (sed -e 's/^ *//g' -e 's/ *$//g')) == "Connected:" ]; then
##		echo "${arr[1]}"
##	fi
#done
#
