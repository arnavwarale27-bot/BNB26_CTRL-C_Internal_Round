def calculate_average(numbers):
    total = 0

    for number in numbers:
        total += number

    return total / len(numbers)


numbers = ["10", "20", "30"]

print(calculate_average(numbers))
