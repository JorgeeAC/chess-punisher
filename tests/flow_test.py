

#####
#       1
#       0   
#    1  0 1 
#    0  1 0
#    1  0 1        

def count_islands(grid):
    if not grid or not grid[0]:
        return 0

    rows = len(grid)
    cols = len(grid[0])
    island_count = 0

    def dfs(r, c):
        # out of bounds
        if r < 0 or r >= rows or c < 0 or c >= cols:
            return

        # water or already visited
        if grid[r][c] != 1:
            return

        # mark as visited
        grid[r][c] = 0

        # explore 4 directions
        dfs(r + 1, c)
        dfs(r - 1, c)
        dfs(r, c + 1)
        dfs(r, c - 1)

    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 1:
                island_count += 1
                dfs(r, c)

    return island_count



grid = [
    [1, 1, 0, 0, 0],
    [1, 1, 0, 0, 1],
    [0, 0, 1, 0, 1],
    [0, 0, 0, 1, 1]
]




def TwoSum(nums, target):
    num_map = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in num_map:
            return [num_map[complement], i]
        num_map[num] = i
    return []




print(count_islands(grid))  


print(TwoSum([2, 7, 11, 15,3,3], 9));