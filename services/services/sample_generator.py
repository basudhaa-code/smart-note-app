import fitz  # PyMuPDF
from pathlib import Path
import config

class SampleLectureGenerator:
    @staticmethod
    def create_sample_lecture_pdf(output_path: Path) -> Path:
        """
        Generates a 4-page university lecture PDF on Deep Learning Foundations
        with formulas, headings, definitions, and study concepts.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc = fitz.open()
        rect = fitz.Rect(45, 45, 550, 800)

        # Page 1: Perceptrons & Activation Functions
        p1 = doc.new_page(width=595, height=842)  # Standard A4
        text_p1 = """CS 601: Advanced Artificial Intelligence & Deep Learning
Lecture 04: Neural Network Foundations & Activation Functions
Instructor: Prof. A. Sterling | Department of Computer Science

1. The Biological and Mathematical Neuron
An Artificial Neuron (Perceptron) is the fundamental computational unit of a neural network. It takes multiple input features x_1, x_2, ..., x_n, multiplies each by a corresponding learnable weight w_1, w_2, ..., w_n, adds a bias term b, and passes the weighted sum through an activation function sigma(z).

Mathematical formulation:
z = sum(w_i * x_i) + b = W^T * X + b
a = sigma(z)

The bias term b allows the activation threshold to shift horizontally, giving the model necessary degrees of freedom. Without a bias, the hyperplane would always be forced to pass through the origin.

2. Activation Functions: Non-Linearity in Deep Networks
Activation functions introduce non-linearities into the network. Without non-linear activation functions, a deep neural network with arbitrary layers collapses mathematically into a single linear transformation: W_2 * (W_1 * X) = (W_2 * W_1) * X = W_combined * X.

Common Activation Functions:
- Sigmoid Function: sigma(z) = 1 / (1 + exp(-z)). Maps inputs into the range (0, 1). Widely used for binary classification outputs. However, it suffers from the Vanishing Gradient problem for very large or very small z, where sigma'(z) approaches 0.
- Hyperbolic Tangent (Tanh): tanh(z) = (exp(z) - exp(-z)) / (exp(z) + exp(-z)). Zero-centered output in range (-1, 1). Preferred over sigmoid for hidden layers.
- Rectified Linear Unit (ReLU): ReLU(z) = max(0, z). Currently the standard default activation for hidden layers. Computationally efficient, prevents vanishing gradients for positive inputs, but can suffer from the 'Dying ReLU' problem when neurons output zero indefinitely.
- Leaky ReLU: LeakyReLU(z) = max(alpha * z, z) where alpha is a small positive constant (e.g. 0.01).
"""
        p1.insert_textbox(rect, text_p1, fontsize=10, fontname="helv")

        # Page 2: Multi-Layer Architectures & Loss Functions
        p2 = doc.new_page(width=595, height=842)
        text_p2 = """CS 601: Advanced Artificial Intelligence & Deep Learning
Lecture 04: Neural Network Foundations (Continued)

3. Multi-Layer Perceptrons (MLP) & Forward Propagation
A Multi-Layer Perceptron consists of an input layer, one or more hidden layers, and an output layer.
In Forward Propagation, signals flow strictly forward from inputs to outputs:
- Hidden Layer 1: z^[1] = W^[1] * a^[0] + b^[1], a^[1] = sigma(z^[1])
- Hidden Layer 2: z^[2] = W^[2] * a^[1] + b^[2], a^[2] = sigma(z^[2])
- Output Layer: z^[L] = W^[L] * a^[L-1] + b^[L], y_hat = a^[L]

The Universal Approximation Theorem states that a feedforward network with a single hidden layer containing a finite number of neurons can approximate any continuous function on compact subsets of R^n, provided the activation function is continuous and non-linear.

4. Objective and Loss Functions
The Loss Function measures the discrepancy between predicted output y_hat and ground truth label y for an individual sample. The Cost Function J(W, b) is the average loss across the entire training dataset.

Common Loss Functions:
- Mean Squared Error (MSE): L(y, y_hat) = 0.5 * (y - y_hat)^2. Primary loss for continuous regression tasks.
- Binary Cross-Entropy (Log Loss): L(y, y_hat) = - [y * log(y_hat) + (1 - y) * log(1 - y_hat)]. Standard for binary classification tasks paired with Sigmoid output.
- Categorical Cross-Entropy: L(y, y_hat) = - sum(y_c * log(y_hat_c)). Used for multi-class classification paired with the Softmax activation function: Softmax(z_i) = exp(z_i) / sum(exp(z_j)).
"""
        p2.insert_textbox(rect, text_p2, fontsize=10, fontname="helv")

        # Page 3: Backpropagation & Optimization Algorithms
        p3 = doc.new_page(width=595, height=842)
        text_p3 = """CS 601: Advanced Artificial Intelligence & Deep Learning
Lecture 04: Neural Network Foundations (Continued)

5. Backpropagation and the Chain Rule of Calculus
Backpropagation is the efficient algorithm used to calculate partial derivatives of the cost function with respect to every weight and bias: partial(J) / partial(W) and partial(J) / partial(b).
By applying the Chain Rule backwards from the output layer:
delta^[L] = partial(J) / partial(z^[L]) = (a^[L] - y)
partial(J) / partial(W^[L]) = (1/m) * delta^[L] * (a^[L-1])^T
partial(J) / partial(b^[L]) = (1/m) * sum(delta^[L])
delta^[l] = ((W^[l+1])^T * delta^[l+1]) * sigma'(z^[l])

6. Gradient Descent and Modern Optimizers
Gradient Descent updates network parameters iteratively in the direction of steepest descent (negative gradient):
theta := theta - alpha * grad(J(theta))
where alpha is the learning rate.

Optimization Variants:
- Batch Gradient Descent: Computes gradients over the complete dataset. Exact and stable, but computationally slow for large scale datasets.
- Stochastic Gradient Descent (SGD): Updates parameters for every single training instance. Extremely fast, but exhibits noisy oscillation.
- Mini-Batch Gradient Descent: Divides data into batches (e.g., 32, 64, 128 samples). Combines vectorization efficiency with regularized convergence.
- Adam Optimizer (Adaptive Moment Estimation): Computes adaptive learning rates for each parameter by storing exponentially decaying averages of past gradients (first moment m_t) and squared gradients (second moment v_t). Currently the most versatile and robust default optimizer in modern deep learning practice.
"""
        p3.insert_textbox(rect, text_p3, fontsize=10, fontname="helv")

        # Page 4: Regularization & Preventing Overfitting
        p4 = doc.new_page(width=595, height=842)
        text_p4 = """CS 601: Advanced Artificial Intelligence & Deep Learning
Lecture 04: Neural Network Foundations (Continued)

7. Overfitting versus Underfitting
- Underfitting (High Bias): The model is too simplistic to capture underlying patterns, resulting in poor performance on both training and validation sets.
- Overfitting (High Variance): The model memorizes training noise rather than true underlying distributions, achieving near-perfect training accuracy but degrading severely on unseen test data.

8. Essential Regularization Techniques
Regularization methods penalize excessive model complexity to improve generalization:
- L2 Regularization (Weight Decay): Adds a penalty term (lambda / 2m) * sum(||W||^2) to the cost function. Forces weights toward zero, effectively smoothing decision boundaries.
- L1 Regularization (Lasso): Adds penalty (lambda / m) * sum(|W|). Drives less important weights to exactly zero, producing sparse models useful for feature selection.
- Dropout: During each training forward pass, randomly deactivates neurons with probability p (typically 0.2 to 0.5). Prevents co-adaptation of neurons and forces redundant representations. During test time, all neurons are active and scaled by (1 - p).
- Early Stopping: Monitors validation loss during training epochs and terminates training when validation loss stops improving, preventing over-training.

9. Lecture Summary & Core Exam Review Points
- Non-linear activations are mandatory to prevent network collapse.
- ReLU is preferred over Sigmoid in hidden layers to avoid vanishing gradients.
- Backpropagation applies the calculus chain rule backwards from loss to input.
- Adam optimizer combines momentum with adaptive per-parameter learning rates.
- Dropout and L2 regularization prevent overfitting and promote generalizable features.
"""
        p4.insert_textbox(rect, text_p4, fontsize=10, fontname="helv")

        doc.save(str(output_path))
        doc.close()
        return output_path
