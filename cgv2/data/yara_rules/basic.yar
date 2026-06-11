rule Suspicious_Shellcode {
    strings:
        $s1 = "shellcode"
        $s2 = "\x90\x90\x90\x90"
    condition:
        any of them
}
