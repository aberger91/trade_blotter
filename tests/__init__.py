from .tests import *


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestBlotter)
    testResult = unittest.TextTestRunner(verbosity=2).run(suite)

