"""EXERCISE SET 2"""

def print_substrs(s):
    # N^2 time, constant space
    for i in range(len(s)):
        for j in range(i+1, len(s) + 1):
            print(s[i:j])


def find_duplicate(arr):
    # N^2 time, constant space
    for i in range(len(arr)):
        for j in range(i+1, len(arr)):
            if arr[i] == arr[j]:
                return arr[i]


def find_sum(arr, target):
    # linear time, linear space
    output = []
    seen = set()
    for i in range(len(arr)):
        for j in range(i+1, len(arr)):
            if arr[i] + arr[j] == target and (arr[i], arr[j]) not in seen:
                output.append([arr[i], arr[j]])
                seen.add((arr[i], arr[j]))
    return list(output)


"EXERCISE SET 1"


def print_zig_zag(arr):
    # wow I did it!!
    #  linear time, constant space

    def in_bounds(row, col, a):
        # true if the square is inside the bounds of the arr
        return 0 <= row < len(a) and 0 <= col < len(a[0])

    def print_up(row, col, a):
        # print diagonally up from a square until limits reached
        # starting square can be outside of matrix
        row_min = 0
        col_max = len(a[0])  # 5
        while row >= row_min and col <= col_max:
            if in_bounds(row, col, a):
                print(a[row][col])
            row -= 1
            col += 1

    def print_down(row, col, a):
        # print diagonally down from a square until limits reached
        row_max = len(a)
        col_min = 0
        while row <= row_max and col >= col_min:
            if in_bounds(row, col, a):
                print(a[row][col])
            row += 1
            col -= 1

    for i in range(max(len(arr) * 2, len(arr[0]) * 2)):
        if i % 2 == 0:
            print_up(row=i, col=0, a=arr)
        if i % 2 == 1:
            print_down(row=0, col=i, a=arr)


"""EXERCISE SET 3 """


def equal_arrs(a1, a2):
    # linear time, constant space
    if len(a1) != len(a2):
        return False
    for i in range(len(a1)):
        if a1[i] != a2[i]:
            return False
    return True


def is_reverse(s1, s2):
    # linear time, constant space
    if len(s1) != len(s2):
        return False
    for i in range(len(s1)):
        if s1[i] != s2[len(s2) - 1 - i]:
            return False
    return True


def is_anagram(s1, s2):
    # linear time, linear space
    if len(s1) != len(s2):
        return False
    from collections import defaultdict
    char_count_1 = defaultdict(int)
    char_count_2 = defaultdict(int)
    for char in s1:
        char_count_1[char] += 1
    for char in s2:
        char_count_2[char] += 1
    return char_count_1 == char_count_2


"""EXERCISE SET 4"""


def calculate_each_k_length_subarray(arr, k):
    # linear time, constant space
    cur_sum = sum(arr[:k])
    output = [cur_sum]
    left = 0
    right = k
    while right < len(arr):
        cur_sum -= arr[left]
        cur_sum += arr[right]
        output.append(cur_sum)
        left += 1
        right += 1
    return output




if __name__ == '__main__':
    #print(print_substrs("abc"))
    #print(find_duplicate([1,2,3,9,5,6,7,8,9]))
    #print(find_sum(arr=[1,2,3,4,5, 3], target=5))
    #print_zig_zag(arr=[[1,2,3,4,5],[6,7,8,9,10],[11,12,13,14,15],[16,17,18,19,20]])
    #print(equal_arrs([1,2,3], [1,2,3]))
    #print(equal_arrs([1,2,3], [4,5,6]))
    #print(is_anagram("abc", "cba"))
    #print(is_anagram("abc", "dba"))
    #print(calculate_each_k_length_subarray([1,2,3,4,5], 3))

