; xorshift16 (7, 9, 8) by hand, John Metcalf's 6502 version, the same
; numbers as gen_xorshift16() in rng.c: its state is xs16_state, and it
; returns the new state, the low byte in A and the high in X.

.section .text.xorshift16_asm,"ax",@progbits
.globl xorshift16_asm
xorshift16_asm:
    lda xs16_state+1
    lsr
    lda xs16_state
    ror
    eor xs16_state+1
    sta xs16_state+1    ; the high byte of x ^= x << 7
    ror                 ; x >> 9
    eor xs16_state
    sta xs16_state      ; x ^= x >> 9, and the low byte of x ^= x << 7
    eor xs16_state+1
    sta xs16_state+1    ; x ^= x << 8
    tax
    lda xs16_state
    rts
