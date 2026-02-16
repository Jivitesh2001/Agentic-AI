def fibonacci(n):
    sequence = [0, 1]
    for i in range(2, n):
        sequence.append(sequence[i-1] + sequence[i-2])
    return sequence[:n]

# Print first 15 Fibonacci numbers
fib_numbers = fibonacci(15)
for num in fib_numbers:
    print(num)