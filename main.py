from input_data import data
from model_construction import math_model

if __name__ == '__main__':
    print("Now starting..")
    print("\t..Now reading data..")
    try:
        inputs = data("new_instance3.csv")
    except Exception as e:
        print("Reading of the data failed. Try again")
        print(e)
    else:
        try:
            print("\t..Now creating model..")
            model = math_model(inputs)
        except Exception as e:
            print("Something went wrong in creating model. Try again")
            print(e)
        else:
            try:
                print("\t..Now solving..")
                model.solve()
            except Exception as e:
                print("Something went wrong in processing. Try again")
                print(e)
