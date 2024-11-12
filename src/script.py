# All your scripts should be in the src/ folder.


from src.utils.tictoc import tic, toc

tic()
x = 5
y = x**2

print(f"{x=}, {y=}")

toc()
