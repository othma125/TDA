from input_data import data
from model_construction import math_model

if __name__ == '__main__':
    print("Now starting..")
    print("\t..Now reading data..")
    try:
        inputs = data("instance2.txt")
    except:
        print("Reading of the data failed. Try again")
        quit()
    try:
        print("\t..Now creating model..")
        model = math_model(inputs)
    except:
        print("Something went wrong in creating model. Try again")
        quit()
    try:
        print("\t..Now solving..")
        model.solve()
    except:
        print("Something went wrong in processing. Try again")
        quit()
